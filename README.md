# pycursor-acp

Python **async** library for driving [Cursor CLI ACP mode](https://cursor.com/docs/cli/acp) (`agent acp`): JSON-RPC 2.0 over stdio, aligned with the Agent Client Protocol.

**Supported Python:** 3.11 or newer (`requires-python = ">=3.11"`).

## PyPI name vs other projects

The **distribution** on PyPI for this repo is **`pycursor-acp`**. The importable **Python package** is **`cursor_acp`** (underscore).

The unrelated PyPI project [`cursor-acp`](https://pypi.org/project/cursor-acp/) (import `cursor_agent`, different API) is not this library. Install with `pip install pycursor-acp` for this codebase.

## Prerequisites

1. **Cursor CLI with ACP** — the `agent` executable from Cursor’s CLI distribution must be **installed and discoverable on `PATH`** (often under `~/.local/bin`). This library spawns:

   - executable: `agent`
   - arguments: `acp`

   Official behavior, transport, and RPC flow are documented at [Cursor CLI: ACP](https://cursor.com/docs/cli/acp).

2. **Python** 3.11+

## Installation

From PyPI:

```bash
pip install pycursor-acp
```

```bash
uv pip install pycursor-acp
```

From this repository:

```bash
pip install "pycursor-acp @ git+https://github.com/Marcelo-Barella/cursor-acp.git@main"
```

```bash
uv pip install "pycursor-acp @ git+https://github.com/Marcelo-Barella/cursor-acp.git@main"
```

Editable install from a local clone:

```bash
pip install -e .
```

```bash
uv pip install -e .
```

**Import vs distribution:** after installation, `import cursor_acp`. The published wheel/sdist name is `pycursor-acp`.

## Minimal async example

```python
import asyncio
from pathlib import Path

from cursor_acp import CursorAcpClient

async def main() -> None:
    your_key = "…"  # application-supplied; injected only into the CLI child env by the library
    async with CursorAcpClient(api_key=your_key, cwd=Path(".")) as client:
        result = await client.prompt("Say hello in one line.")
    print(result["stopReason"])

asyncio.run(main())
```

`CursorAcpClient` requires a non-empty **`api_key`** string; the library does not read secrets from the parent process environment for session auth.

## Credentials and environment variables (official names)

Per [Cursor CLI ACP authentication](https://cursor.com/docs/cli/acp) (verified against this implementation’s subprocess env builder in `cursor_acp.env`), the **exact** environment variable names recognized for CLI auth are:

| Variable | Role (per Cursor docs) |
| -------- | ---------------------- |
| `CURSOR_API_KEY` | API key; CLI also accepts `--api-key` |
| `CURSOR_AUTH_TOKEN` | Auth token; CLI also accepts `--auth-token` |

**What this library does:** `build_cursor_acp_subprocess_environ` copies a snapshot of the parent environment (or a caller-supplied `source` mapping), **removes** both `CURSOR_API_KEY` and `CURSOR_AUTH_TOKEN` so ambient credentials cannot silently override the explicit `api_key` argument, then sets **`CURSOR_API_KEY`** in the **child** environment to the validated constructor `api_key`. It does **not** mutate `os.environ` in the parent process.

**Reproducibility:** record `cursor_acp.__version__` and the Cursor CLI build reported by your installation (for example `agent --version` when supported) alongside any bug reports; this repository does not pin a single Cursor CLI version—behavior should track `https://cursor.com/docs/cli/acp` and your installed binary.

## Security

- **Child-only injection:** API keys are passed to the `agent acp` subprocess via that process’s environment dict. Do not rely on (or implement) parent-process `os.environ` mutation to “inject” credentials for this client.
- **No logging of secrets:** do not log API keys or tokens; avoid putting secrets in exception messages or user-visible `repr()` output. Library errors follow that boundary (see `cursor_acp.exceptions`).
- **Explicit `api_key`:** supply credentials from your app’s secret store or config; treat them like any other high-entropy secret.

## Implementation strategy

**Chosen fork: (A)** — Prefer **contributing upstream** to [`github.com/azgo14/cursor-agent`](https://github.com/azgo14/cursor-agent) while keeping **`pycursor-acp`** contracts: **constructor-required `api_key`**, **subprocess-isolated environment** (no parent env mutation), and **documentation / tests parity** with Cursor’s official ACP docs and verified CLI behavior.

**Rationale (brief):** The protocol and transport are specified by Cursor’s CLI and ACP documentation; this package uses a distinct PyPI name (`pycursor-acp`) so installs are unambiguous vs the separate `cursor-acp` distribution.

**Upstream reference (not a shipping name):** use [`github.com/azgo14/cursor-agent`](https://github.com/azgo14/cursor-agent) as a comparison and contribution target when proposing protocol or packaging changes; it is not the import path for this tree.

## Development

```bash
pip install -e ".[dev]"
```

**Lint and format:** this repository uses **[Ruff](https://docs.astral.sh/ruff/)** for lint (`E,F,I,UP,W`) and formatting.

```bash
python3 -m ruff check .
python3 -m ruff format --check .
```

**Static typing:** checked with **[mypy](https://mypy-lang.org/)** in **strict** mode on the packaged sources under `src/`.

```bash
python3 -m mypy src
```

**Tests:** CI and local default runs omit integration tests (marked `integration`; require real Cursor CLI and credentials).

```bash
python3 -m pytest -m "not integration"
```

To include integration gates when you have `agent` on `PATH` and credentials, see `CURSOR_ACP_INTEGRATION` / `CURSOR_API_KEY` in `pyproject.toml` markers.

See [CHANGELOG.md](CHANGELOG.md) for release notes.
