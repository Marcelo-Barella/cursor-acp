from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from cursor_acp import (
    CursorAcpAuthError,
    CursorAcpCancelledError,
    CursorAcpClient,
    CursorAcpCliNotFoundError,
    CursorAcpTimeoutError,
)

_FAKE_AGENT = """#!/usr/bin/env python3
import json
import sys

PROTO = "2.0"
stdin = sys.stdin.buffer
stdout = sys.stdout.buffer

for raw in stdin:
    line = raw.decode()
    if not line.strip():
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    mid = msg.get("id")
    method = msg.get("method")
    if mid is None or method is None:
        continue
    if method == "initialize":
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
    elif method == "authenticate":
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
    elif method == "session/new":
        out = {
            "jsonrpc": PROTO,
            "id": mid,
            "result": {"sessionId": "sess_test"},
        }
    elif method == "session/prompt":
        out = {
            "jsonrpc": PROTO,
            "id": mid,
            "result": {"stopReason": "end_turn"},
        }
    elif method == "ping":
        out = {"jsonrpc": PROTO, "id": mid, "result": "pong"}
    else:
        out = {
            "jsonrpc": PROTO,
            "id": mid,
            "error": {"code": -32601, "message": method},
        }
    stdout.write((json.dumps(out) + chr(10)).encode())
    stdout.flush()
"""


@pytest.mark.asyncio
async def test_cursor_acp_client_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    client = CursorAcpClient(api_key="k", cwd=tmp_path)
    assert await client.prompt("hello") == {"stopReason": "end_turn"}
    await client.shutdown()


@pytest.mark.asyncio
async def test_cursor_acp_client_context_manager(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    async with CursorAcpClient(api_key="k", cwd=tmp_path) as client:
        assert await client.prompt("hello") == {"stopReason": "end_turn"}


@pytest.mark.asyncio
async def test_cursor_acp_client_prompt_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hang = """#!/usr/bin/env python3
import json
import sys
import time
stdin = sys.stdin.buffer
stdout = sys.stdout.buffer
for raw in stdin:
    line = raw.decode()
    if not line.strip():
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    mid = msg.get("id")
    method = msg.get("method")
    if mid is None or method is None:
        continue
    if method == "initialize":
        out = {"jsonrpc": "2.0", "id": mid, "result": {}}
    elif method == "authenticate":
        time.sleep(10)
        out = {"jsonrpc": "2.0", "id": mid, "result": {}}
    else:
        out = {"jsonrpc": "2.0", "id": mid, "result": {}}
    stdout.write((json.dumps(out) + chr(10)).encode())
    stdout.flush()
"""
    exe = tmp_path / "agent"
    exe.write_text(hang)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    client = CursorAcpClient(api_key="k", cwd=tmp_path, handshake_timeout=0.2)
    with pytest.raises(CursorAcpTimeoutError):
        await client.start()
    await client.shutdown()


@pytest.mark.asyncio
async def test_cursor_acp_client_prompt_cancelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    client = CursorAcpClient(api_key="k", cwd=tmp_path)
    await client.start()

    task = asyncio.create_task(client.prompt("x"))
    asyncio.get_event_loop().call_soon(lambda: task.cancel())
    with pytest.raises(CursorAcpCancelledError):
        await task
    await client.shutdown()


@pytest.mark.asyncio
async def test_cli_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    client = CursorAcpClient(api_key="k", cwd=tmp_path)
    with pytest.raises(CursorAcpCliNotFoundError):
        await client.start()


_FAKE_FAIL_AUTH = """#!/usr/bin/env python3
import json
import sys
PROTO = "2.0"
stdin = sys.stdin.buffer
stdout = sys.stdout.buffer
for raw in stdin:
    line = raw.decode()
    if not line.strip():
        continue
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        continue
    mid = msg.get("id")
    method = msg.get("method")
    if mid is None or method is None:
        continue
    if method == "initialize":
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
    elif method == "authenticate":
        out = {
            "jsonrpc": PROTO,
            "id": mid,
            "error": {"code": 401, "message": "nope"},
        }
    else:
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
    stdout.write((json.dumps(out) + chr(10)).encode())
    stdout.flush()
"""


@pytest.mark.asyncio
async def test_authenticate_jsonrpc_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_FAIL_AUTH)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    client = CursorAcpClient(api_key="k", cwd=tmp_path)
    with pytest.raises(CursorAcpAuthError):
        await client.start()
