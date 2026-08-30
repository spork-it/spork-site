"""End-to-end coverage for the project-local ``spork site`` provider."""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from spork.project.dist import create_dist


def run_spork(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PIP_NO_CACHE_DIR"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "spork", *arguments],
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"spork {' '.join(arguments)} failed with {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def project_python(project: Path) -> Path:
    candidates = [
        project / ".venv" / "bin" / "python",
        project / ".venv" / "Scripts" / "python.exe",
    ]
    selected = next((candidate for candidate in candidates if candidate.is_file()), None)
    assert selected is not None, "project Python interpreter was not created"
    return selected


def wait_for_output(
    lines: list[str], process: subprocess.Popen[str], fragment: str, timeout: float = 30
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(fragment in line for line in lines):
            return
        if process.poll() is not None:
            raise AssertionError(
                f"development server exited with {process.returncode}\n{''.join(lines)}"
            )
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {fragment!r}\n{''.join(lines)}")


def read_reload_event(response: object, timeout: float = 30) -> bytes:
    completed: queue.Queue[bytes | BaseException] = queue.Queue()

    def consume() -> None:
        block: list[bytes] = []
        try:
            while True:
                line = response.readline()  # type: ignore[attr-defined]
                if not line:
                    raise EOFError("reload event stream closed")
                block.append(line)
                if line == b"\n":
                    if any(item.startswith(b"event: reload") for item in block):
                        completed.put(b"".join(block))
                        return
                    block = []
        except BaseException as error:  # pragma: no cover - asserted in caller
            completed.put(error)

    threading.Thread(target=consume, daemon=True).start()
    result = completed.get(timeout=timeout)
    if isinstance(result, BaseException):
        raise result
    return result


def test_source_only_consumer_uses_project_site_provider(tmp_path: Path) -> None:
    repository = Path(__file__).resolve().parents[1]
    distribution = create_dist(
        project_root=repository,
        out_dir=tmp_path / "provider-build",
        dist_dir=tmp_path / "provider-dist",
        clean=True,
        verbose=False,
    )
    assert distribution.success, distribution.error
    assert distribution.wheel_path is not None

    consumer = tmp_path / "consumer"
    shutil.copytree(repository / "tests" / "fixtures" / "command-site", consumer)
    for template in consumer.rglob("*.spork.template"):
        template.rename(template.with_suffix(""))
    manifest = consumer / "spork.it"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "__SPORK_SITE_REQUIREMENT__",
            f"spork-site @ {distribution.wheel_path.resolve().as_uri()}",
        ),
        encoding="utf-8",
    )

    # This is the normal project workflow: synchronization installs both the
    # compatible command host and the provider wheel into the project venv.
    run_spork(consumer, "sync", "--quiet")
    assert not (consumer / ".spork-out").exists()

    nested = consumer / "work" / "nested"
    nested.mkdir(parents=True)

    help_result = run_spork(nested, "site", "--help")
    assert "usage: spork site" in help_result.stdout
    for command_name in ("build", "check", "clean", "routes", "serve", "version"):
        assert command_name in help_result.stdout

    check_result = run_spork(nested, "site", "check", "--json")
    checked = json.loads(check_result.stdout)
    assert checked == {
        "assets": 1,
        "files": 3,
        "output": str((consumer / "public").resolve()),
        "pages": 2,
    }
    assert not (consumer / "public").exists()

    routes_result = run_spork(nested, "site", "routes", "--json")
    assert json.loads(routes_result.stdout) == [
        {"output": "docs/index.html", "route": "/docs/"},
        {"output": "index.html", "route": "/"},
    ]
    assert not (consumer / "public").exists()

    public = consumer / "public"
    public.mkdir()
    retained = public / "retained.txt"
    retained.write_text("keep", encoding="utf-8")
    build_result = run_spork(nested, "site", "build", "--no-clean", "--json")
    built = json.loads(build_result.stdout)
    assert built["assets"] == 1
    assert built["pages"] == 2
    assert built["output"] == str(public.resolve())
    assert built["written"] == ["docs/index.html", "index.html", "site.css"]
    assert isinstance(built["duration_seconds"], float)
    assert retained.is_file()
    assert "Built directly from <strong>Spork source</strong>." in (
        public / "index.html"
    ).read_text(encoding="utf-8")

    # A normal build cleans stale files, while the application entry point is
    # still completely independent from the site factory.
    run_spork(nested, "site", "build")
    assert not retained.exists()
    app_result = run_spork(nested, "run")
    assert app_result.stdout.strip() == "application main"

    run_spork(nested, "site", "clean")
    assert not public.exists()

    preview = consumer / "preview"
    run_spork(nested, "site", "build", "--output", "preview")
    assert (preview / "index.html").is_file()
    run_spork(nested, "site", "clean", "--output", "preview")
    assert not preview.exists()

    version_result = run_spork(nested, "site", "version")
    assert "spork-site 0.1.1" in version_result.stdout
    assert "Spork host: 0.6.0" in version_result.stdout
    assert "Provider: spork-site (project)" in version_result.stdout

    # Development mode serves isolated full-build generations. Related events
    # are debounced, successful builds notify SSE clients, and a broken source
    # rebuild leaves the last complete generation available until recovery.
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUNBUFFERED"] = "1"
    process = subprocess.Popen(
        [
            str(project_python(consumer)),
            "-m",
            "spork",
            "site",
            "serve",
            "--port",
            "0",
        ],
        cwd=nested,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    assert process.stdout is not None
    output_lines: list[str] = []

    def collect_output() -> None:
        assert process.stdout is not None
        output_lines.extend(process.stdout)

    collector = threading.Thread(target=collect_output, daemon=True)
    collector.start()
    index_source = consumer / "content" / "index.md"
    stylesheet = consumer / "static" / "site.css"
    site_source = consumer / "src" / "source_site" / "site.spork"
    original_index = index_source.read_text(encoding="utf-8")
    original_stylesheet = stylesheet.read_text(encoding="utf-8")
    original_site = site_source.read_text(encoding="utf-8")
    events = None
    try:
        wait_for_output(output_lines, process, "Serving ")
        serving_line = next(line for line in output_lines if "Serving " in line)
        match = re.search(r"at (http://\S+)", serving_line)
        assert match is not None
        url = match.group(1)

        with urllib.request.urlopen(url, timeout=10) as response:
            initial_html = response.read()
            assert response.status == 200
            assert response.headers["X-Spork-Site-Generation"] == "1"
            assert b"Built directly from <strong>Spork source</strong>." in initial_html
            assert b"data-spork-site-reload" in initial_html
        with urllib.request.urlopen(f"{url}site.css", timeout=10) as response:
            assert response.status == 200
            assert response.headers["Content-Type"].startswith("text/css")
            assert b"data-spork-site-reload" not in response.read()
        assert not public.exists()

        events = urllib.request.urlopen(
            f"{url.rstrip('/')}/_spork-site/reload", timeout=30
        )
        index_source.write_text(
            f"{original_index}\nDevelopment reload marker.\n", encoding="utf-8"
        )
        stylesheet.write_text(
            f"{original_stylesheet}\n/* related debounce marker */\n",
            encoding="utf-8",
        )
        first_event = read_reload_event(events)
        assert b"event: reload" in first_event
        assert b"data: 2" in first_event
        wait_for_output(output_lines, process, "Rebuilt generation 2")
        changed_line = next(
            line
            for line in output_lines
            if "Changed:" in line and "content/index.md" in line
        )
        assert "static/site.css" in changed_line
        time.sleep(0.5)
        assert sum("Rebuilt generation" in line for line in output_lines) == 1

        with urllib.request.urlopen(url, timeout=10) as response:
            stable_html = response.read()
            stable_generation = response.headers["X-Spork-Site-Generation"]
            assert b"Development reload marker." in stable_html

        site_source.write_text(
            f'{original_site}\n(throw (RuntimeError "development failure"))\n',
            encoding="utf-8",
        )
        wait_for_output(output_lines, process, "Build failed after")
        wait_for_output(output_lines, process, "continuing to serve generation 2")
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.headers["X-Spork-Site-Generation"] == stable_generation
            assert b"Development reload marker." in response.read()

        site_source.write_text(original_site, encoding="utf-8")
        recovered_event = read_reload_event(events)
        assert b"event: reload" in recovered_event
        assert b"data: 3" in recovered_event
        wait_for_output(output_lines, process, "Rebuilt generation 4")
        with urllib.request.urlopen(url, timeout=10) as response:
            assert response.headers["X-Spork-Site-Generation"] == "4"
            assert b"Development reload marker." in response.read()
        assert not public.exists()
    finally:
        index_source.write_text(original_index, encoding="utf-8")
        stylesheet.write_text(original_stylesheet, encoding="utf-8")
        site_source.write_text(original_site, encoding="utf-8")
        if events is not None:
            events.close()
        if process.poll() is None:
            process.send_signal(getattr(signal, "CTRL_BREAK_EVENT", signal.SIGINT))
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        collector.join(timeout=5)

    assert process.returncode == 0, "".join(output_lines)
    assert "Development server stopped." in "".join(output_lines)
    assert sum("Rebuilt generation" in line for line in output_lines) == 2
    assert not public.exists()
    assert not (consumer / ".spork-out").exists()
