## Cursor Cloud specific instructions

**Product:** `pycursor-acp` -- a Python async client library for Cursor CLI ACP mode (JSON-RPC 2.0 over stdio). Pure Python, no runtime dependencies beyond stdlib.

**Python version:** 3.11+ (VM has 3.12). No need for pyenv/mise; system Python works.

**Install:** `pip install -e ".[dev]"` from the repo root. This installs mypy, pytest, pytest-asyncio, ruff, and twine.

**PATH caveat:** pip installs scripts to `/home/ubuntu/.local/bin`. Ensure this is on PATH (already added to `~/.bashrc`). Alternatively prefix commands with `python3 -m`.

**Commands** (all from repo root, documented in README):
- Lint: `python3 -m ruff check .`
- Format check: `python3 -m ruff format --check .`
- Type check: `python3 -m mypy src`
- Unit tests: `python3 -m pytest -m "not integration"`

**Integration tests** require the Cursor CLI `agent` binary on PATH and a `CURSOR_API_KEY` secret. They are skipped by default via the `integration` pytest marker. Do not attempt to run them without the binary.

**No services to start:** This is a library, not an application. There is no server, database, or docker-compose setup. Development is purely lint/typecheck/test.
