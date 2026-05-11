from __future__ import annotations

import asyncio
import json
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
import os
import sys

PROTO = "2.0"
stdin = sys.stdin.buffer
stdout = sys.stdout.buffer
LOG = os.environ.get("CURSOR_ACP_FAKE_RPC_LOG")

def log_entry(payload):
    if not LOG:
        return
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload) + chr(10))

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
    params = msg.get("params")
    log_entry({"method": method, "params": params})
    if method == "initialize":
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
    elif method == "authenticate":
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
    elif method == "session/new":
        out = {
            "jsonrpc": PROTO,
            "id": mid,
            "result": {
                "sessionId": "sess_test",
                "modes": {
                    "currentModeId": "agent",
                    "availableModes": [
                        {"id": "agent", "name": "Agent"},
                        {"id": "plan", "name": "Plan"},
                        {"id": "ask", "name": "Ask"},
                    ],
                },
            },
        }
    elif method == "session/set_mode":
        out = {"jsonrpc": PROTO, "id": mid, "result": {}}
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
async def test_plan_mode_triggers_session_set_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "rpc.log"
    monkeypatch.setenv("CURSOR_ACP_FAKE_RPC_LOG", str(log))
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    client = CursorAcpClient(api_key="k", cwd=tmp_path, mode="plan")
    await client.start()
    calls = [json.loads(line)["method"] for line in log.read_text().splitlines()]
    assert calls.count("session/set_mode") == 1
    set_calls = [
        json.loads(line)
        for line in log.read_text().splitlines()
        if json.loads(line)["method"] == "session/set_mode"
    ]
    assert set_calls[0]["params"] == {"sessionId": "sess_test", "modeId": "plan"}
    await client.shutdown()


@pytest.mark.asyncio
async def test_prompt_mode_override_triggers_set_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log = tmp_path / "rpc.log"
    monkeypatch.setenv("CURSOR_ACP_FAKE_RPC_LOG", str(log))
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    client = CursorAcpClient(api_key="k", cwd=tmp_path, mode="plan")
    assert await client.prompt("x", mode="ask") == {"stopReason": "end_turn"}
    calls = [json.loads(line)["method"] for line in log.read_text().splitlines()]
    assert calls.count("session/set_mode") == 2
    set_calls = [
        json.loads(line)
        for line in log.read_text().splitlines()
        if json.loads(line)["method"] == "session/set_mode"
    ]
    assert set_calls[0]["params"]["modeId"] == "plan"
    assert set_calls[1]["params"]["modeId"] == "ask"
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
