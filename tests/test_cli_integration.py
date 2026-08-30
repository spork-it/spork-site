"""End-to-end coverage for the project-local ``spork site`` provider."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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
    for command_name in ("build", "check", "clean", "routes", "version"):
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
    assert "spork-site 0.1.0" in version_result.stdout
    assert "Spork host: 0.6.0" in version_result.stdout
    assert "Provider: spork-site (project)" in version_result.stdout
    assert not (consumer / ".spork-out").exists()
