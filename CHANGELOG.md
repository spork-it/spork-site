# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-08-30

### Added

- Immutable `Element`, `Fragment`, `Text`, and `RawHtml` node types.
- Locally scoped `(markup ...)` blocks with `$tag` lowering.
- Deterministic attribute normalization and escaped HTML serialization.
- CommonMark parsing and conversion into the shared immutable node model.
- Generic immutable post-order node transformations.
- YAML front matter and deterministic recursive Markdown discovery.
- Persistent content collections with eager filtering, sorting, and limits.
- Clean static routes, generated pages, layouts, and conflict detection.
- Deterministic static builds with copied assets and safe output cleanup.
- Structural Pygments syntax highlighting for fenced code blocks.
- Deterministic sitemap, RSS 2.0, and Atom 1.0 generation.
- A `spork.commands.v1` provider for the complete `spork site ...` CLI.
- Context-based loading of ordinary source-only site factories from `:site :target`.
- Nested build, non-writing check, site-aware clean, routes, and provenance-aware version commands with JSON output where applicable.
- End-to-end fixture blog and source-only consumer coverage plus cross-platform CI/CD automation.

### Changed

- Require Spork 0.6 for command-provider metadata and project source loading.
- Make `spork site ...` the primary workflow while retaining the built-module `spork run` facade temporarily for compatibility.

[Unreleased]: https://github.com/spork-it/spork-site/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/spork-it/spork-site/releases/tag/v0.1.0
