from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from cursor_acp import CursorAcpClient
from dotenv import load_dotenv

ACP_ARGV: tuple[str, ...] = ("--model", "composer-2", "acp")


def _quit(line: str) -> bool:
    t = line.strip().lower()
    return t in ("quit", "exit", "q")


def _api_key() -> str:
    load_dotenv()
    return (os.environ.get("CURSOR_API_KEY") or "").strip()


async def _repl(client: CursorAcpClient) -> None:
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if line == "":
            break
        if _quit(line):
            break
        text = line.rstrip("\n\r")
        if not text.strip():
            continue
        result = await client.prompt(text)
        print("stopReason:", result.get("stopReason"))
        print(json.dumps(result, indent=2))


async def _amain() -> None:
    key = _api_key()
    if not key:
        print(
            "CURSOR_API_KEY is missing. Set it in the environment (e.g. Cursor "
            "secrets) or in a .env file next to this script. See .env.example.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    cwd = Path.cwd()
    async with CursorAcpClient(api_key=key, cwd=cwd, acp_argv=ACP_ARGV) as client:
        await _repl(client)


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        print("", file=sys.stderr)


if __name__ == "__main__":
    main()
