# cursor-acp

Python **async** library for driving [Cursor CLI ACP mode](https://cursor.com/docs/cli/acp) (`agent acp`): JSON-RPC 2.0 over stdio, aligned with the Agent Client Protocol.

**Supported Python:** 3.11 or newer (`requires-python = ">=3.11"`).

## PyPI package name status (read before `pip install`)

The intended **distribution** name for this project is **`cursor-acp`** (hyphenated, as on package indexes). The importable **Python package** is **`cursor_acp`** (underscore).

**Naming collision:** As of 2026-05-08, the PyPI project [`cursor-acp`](https://pypi.org/project/cursor-acp/) already exists and is owned by `azgo14`, with source and metadata pointing at [`github.com/azgo14/cursor-agent`](https://github.com/azgo14/cursor-agent). That publication’s README documents a **`cursor_agent`** import and a different public API than this repository’s **`cursor_acp`** / `CursorAcpClient`.

**Resolution (before claiming the index name):** Do not assume `pip install cursor-acp` installs this codebase. Until maintainers coordinate (for example upstream alignment per the implementation strategy below, a new distribution name such as a clearly distinct PyPI name, or a PEP 541 name request where applicable), install **this** project from a **Git URL** or a **local checkout**. Re-check PyPI immediately before any release, because index state can change.

## Prerequisites

1. **Cursor CLI with ACP** — the `agent` executable from Cursor’s CLI distribution must be **installed and discoverable on `PATH`** (often under `~/.local/bin`). This library spawns:

   - executable: `agent`
   - arguments: `acp`

   Official behavior, transport, and RPC flow are documented at [Cursor CLI: ACP](https://cursor.com/docs/cli/acp).

2. **Python** 3.11+

## Installation

From this repository (recommended until the PyPI name situation is resolved):

```bash
pip install "cursor-acp @ git+https://github.com/Marcelo-Barella/cursor-acp.git@main"
```

```bash
uv pip install "cursor-acp @ git+https://github.com/Marcelo-Barella/cursor-acp.git@main"
```

Editable install from a local clone:

```bash
pip install -e .
```

```bash
uv pip install -e .
```

**Import vs distribution:** after installation, `import cursor_acp`. The distribution name you pass to installers is typically `cursor-acp` for a published wheel/sdist; VCS installs above use a PEP 508 URL with a local package name label (`cursor_acp` in the examples) for clarity.

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

**Chosen fork: (A)** — Prefer **contributing upstream** to [`github.com/azgo14/cursor-agent`](https://github.com/azgo14/cursor-agent) while keeping the **cursor-acp** product identity and contracts in this line of work: **constructor-required `api_key`**, **subprocess-isolated environment** (no parent env mutation), and **documentation / tests parity** with Cursor’s official ACP docs and verified CLI behavior.

**Rationale (brief):** The protocol and transport are specified and maintained by Cursor’s CLI and ACP documentation; duplicating or vendoring the full protocol stack under a parallel PyPI name fragments fixes and security review. Upstream already publishes on PyPI under `cursor-acp` with overlapping scope; consolidating improvements reduces user confusion once naming and API alignment are sorted, while this repository can still articulate the stricter API-key boundary and env-isolation guarantees as requirements for merges.

The alternative **(B)** — fully owning `cursor-acp` behind a thin wrapper or vendored protocol — is **not** selected here, because it increases long-term divergence from the de-facto reference implementation and does not by itself resolve the existing **`cursor-acp`** index conflict.

**Upstream reference (not a shipping name):** use [`github.com/azgo14/cursor-agent`](https://github.com/azgo14/cursor-agent) as a comparison and contribution target when proposing protocol or packaging changes; it is not the import path for this tree.

## Development

```bash
pip install -e ".[dev]"
python3 -m pytest
```

Integration-style tests may be gated; see `pyproject.toml` markers.

See [CHANGELOG.md](CHANGELOG.md) for release notes.
