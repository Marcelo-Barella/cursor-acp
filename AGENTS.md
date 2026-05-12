# AGENTS.md

## Cursor Cloud specific instructions

This is `pycursor-acp`, a pure Python async library (PyPI: `pycursor-acp`, import: `cursor_acp`) for driving the Cursor CLI ACP mode via JSON-RPC 2.0 over stdio. Python 3.11+ required.

### Environment

A virtualenv at `.venv/` is created and managed by the update script. Always activate it before running any commands:

```bash
source .venv/bin/activate
```

### Commands (all from repo root, with venv activated)

| Task | Command |
|------|---------|
| Lint | `python3 -m ruff check .` |
| Format check | `python3 -m ruff format --check .` |
| Type check | `python3 -m mypy src` |
| Unit tests | `python3 -m pytest -m "not integration"` |
| Integration tests | `python3 -m pytest -m integration` (requires `agent` binary on PATH + `CURSOR_API_KEY`) |

### Gotchas

- The system Python may lack `python3.12-venv`. The update script installs it via `sudo apt-get`.
- Integration tests require the Cursor CLI `agent` binary and a `CURSOR_API_KEY` env var. Unit tests run fully offline with mocks.
- `uv` is not pre-installed in the VM; the update script installs it but uses `pip` for the editable install since `uv pip install -e` can hit permission issues with hardlinks. Standard `pip` inside `.venv` works reliably.
