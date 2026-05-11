from __future__ import annotations

import os
from pathlib import Path

import pytest

from cursor_acp.stdio_jsonrpc import (
    CursorCliAcpStdioJsonRpc,
    _coerce_request_id_key,
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


def test_coerce_request_id_key() -> None:
    assert _coerce_request_id_key(7) == 7
    assert _coerce_request_id_key("42") == 42
    assert _coerce_request_id_key(True) is None
    assert _coerce_request_id_key("not-int") is None


@pytest.mark.asyncio
async def test_stdio_json_rpc_request_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")

    cli = CursorCliAcpStdioJsonRpc(api_key="test-key-nonempty", cwd=tmp_path)
    await cli.start(handshake_timeout=30.0, auto_initialize=True)
    try:
        assert await cli.request("ping", {}, timeout=10.0) == "pong"
    finally:
        await cli.aclose()
