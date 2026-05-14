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


async def _main() -> None:
    load_dotenv()
    api_key = (os.environ.get("CURSOR_API_KEY") or "").strip()
    if not api_key:
        print("CURSOR_API_KEY is empty; set it in .env", file=sys.stderr)
        raise SystemExit(1)
    cwd = Path.cwd()
    async with CursorAcpClient(
        api_key,
        cwd,
        acp_argv=ACP_ARGV,
    ) as client:
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, lambda: sys.stdin.readline())
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


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
