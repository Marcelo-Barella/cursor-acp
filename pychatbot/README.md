# pychatbot

Small async stdin loop around [`pycursor-acp`](https://pypi.org/project/pycursor-acp/) (`import cursor_acp`).

## Requirements

- Python 3.11 or newer
- Cursor `agent` CLI with ACP on your `PATH` (see the root [README.md](../README.md))
- A `CURSOR_API_KEY` value supplied either from your process environment (for example **Cursor agent secrets** / CI variables) or from a local `.env` file. `python-dotenv` is loaded with default `override=False`, so an already-set `CURSOR_API_KEY` in the environment is **not** replaced by `.env`. The library still passes the key explicitly into the `agent` child; it does not depend on the child inheriting the parent credential env entries for auth.

## Setup

```bash
cd pychatbot
python3 -m pip install -r requirements.txt
```

Copy [`.env.example`](.env.example) to `.env` and fill in your key, or export `CURSOR_API_KEY` in the shell / agent secret store instead.

## Run

```bash
python3 main.py
```

or:

```bash
python3 chat.py
```

Type a line and press Enter to send it to `session/prompt`. Commands `quit`, `exit`, or `q` stop the loop (EOF also exits).

## Model: `composer-2`

The v1 `CursorAcpClient.prompt` implementation sends only `sessionId` and `prompt` (text blocks) on `session/prompt`; **the JSON-RPC prompt payload cannot select the model** for that turn.

This sample selects **composer-2** the supported CLI way: global [`--model`](https://cursor.com/docs/cli/reference/parameters) before the `acp` subcommand, by passing `acp_argv=("--model", "composer-2", "acp")` so the child process is `agent --model composer-2 acp`. That matches Cursor’s documented global options (not a per-prompt field). There is no separate model parameter on `session/new` in the client API used here; model is not taken from an official env var in the parameters docs—use CLI flags (or your own `cli_executable` / wrapper) if you need a different model.
