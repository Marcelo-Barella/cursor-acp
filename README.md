# cursor-acp

Python library for Cursor Agent Client Protocol (ACP) integration.

**Status:** early scaffolding. Requires Python 3.11 or newer.

Install from a source checkout (not published to PyPI yet):

```bash
pip install .
```

Import the package as `cursor_acp` (the published distribution name is `cursor-acp`).

ACP transport framing and RPC methods follow Cursor CLI docs: [ACP](https://cursor.com/docs/cli/acp). When debugging, record the Cursor CLI build version from your installation (when available via `agent --version` or your package manager) next to ``cursor_acp.__version__``.

See [CHANGELOG.md](CHANGELOG.md) for release notes.
