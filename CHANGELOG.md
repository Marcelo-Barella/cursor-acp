# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-11

### Added

- ACP interaction modes (`agent`, `plan`, `ask`): `CursorAcpClient` constructor `mode`, `start(mode=...)`, and per-call `prompt(..., mode=...)` with `session/set_mode` RPC when the session mode differs; exported `CursorAcpInteractionMode`.
- Async subprocess transport for Cursor CLI ACP mode: newline-delimited JSON-RPC 2.0 over stdio (`cursor_acp.CursorCliAcpStdioJsonRpc`), subprocess environment built from an explicit non-mutating snapshot with `CURSOR_API_KEY` injected from a required `api_key` parameter (ambient credential env vars are stripped by default). API key validation uses `CursorAcpApiKeyError`.

### Changed

- PyPI distribution name is `pycursor-acp` (Python import remains `cursor_acp`). Default JSON-RPC `clientName` is `pycursor-acp`.
- Package metadata: real authors and maintainers in `pyproject.toml`; dev optional dependency `twine`.

## [0.1.0] - PLACEHOLDER_RELEASE_DATE

### Added

- Initial library scaffolding: `pyproject.toml` packaging for Python 3.11 and later, `src/` layout.
- Public package import path `cursor_acp` (distribution name `cursor-acp`).
- MIT licensed source tree.

[0.2.0]: https://github.com/Marcelo-Barella/cursor-acp/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Marcelo-Barella/cursor-acp/releases/tag/v0.1.0
