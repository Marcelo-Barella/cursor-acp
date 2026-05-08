from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cursor_acp import CursorAcpClient
from cursor_acp.exceptions import CursorAcpApiKeyError, CursorAcpSpawnError

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
    else:
        out = {
            "jsonrpc": PROTO,
            "id": mid,
            "error": {"code": -32601, "message": method},
        }
    stdout.write((json.dumps(out) + chr(10)).encode())
    stdout.flush()
"""


def _install_fake_agent(tmp_path: Path) -> None:
    exe = tmp_path / "agent"
    exe.write_text(_FAKE_AGENT)
    exe.chmod(0o755)


def _assert_no_substring_in_text(text: str, secret: str) -> None:
    if not secret:
        raise AssertionError("secret marker must be non-empty")
    assert secret not in text


@pytest.mark.parametrize(
    "api_key",
    ["", "   ", "\t\n", " \r\n "],
)
def test_cursor_acp_client_rejects_blank_api_key(api_key: str) -> None:
    with pytest.raises(CursorAcpApiKeyError):
        CursorAcpClient(api_key=api_key, cwd=Path("."))


def test_cursor_acp_client_api_key_error_is_typed() -> None:
    with pytest.raises(CursorAcpApiKeyError) as info:
        CursorAcpClient(api_key="", cwd=Path("."))
    assert type(info.value) is CursorAcpApiKeyError


@pytest.mark.asyncio
async def test_parent_os_environ_unchanged_after_client_spawn_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _install_fake_agent(tmp_path)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    secret = "cursor_acp_unit_test_secret_7a2f9e1c4b8d0f3a"
    before = dict(os.environ)
    assert secret not in "".join(before.values())

    caplog.set_level(logging.INFO, logger="cursor_acp.stdio_jsonrpc")

    client = CursorAcpClient(api_key=secret, cwd=tmp_path)
    try:
        await client.start()
        await client.prompt("x")
    finally:
        await client.shutdown()

    after = dict(os.environ)
    assert after == before
    _assert_no_substring_in_text(caplog.text, secret)


@pytest.mark.asyncio
async def test_spawn_config_double_does_not_leak_secret_to_parent_environ(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _install_fake_agent(tmp_path)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ.get('PATH', '')}")
    secret = "cursor_acp_spawn_cfg_marker_91c4e7b2a5d8f601"
    before = dict(os.environ)

    caplog.set_level(logging.DEBUG, logger="cursor_acp.stdio_jsonrpc")

    captured: dict[str, object] = {}

    async def fake_create_subprocess_exec(*args: object, **kwargs: object) -> None:
        captured["env"] = kwargs.get("env")
        raise OSError("injected spawn failure for env capture")

    client = CursorAcpClient(api_key=secret, cwd=tmp_path)
    with patch(
        "cursor_acp.stdio_jsonrpc.asyncio.create_subprocess_exec",
        new_callable=AsyncMock,
        side_effect=fake_create_subprocess_exec,
    ):
        with pytest.raises(CursorAcpSpawnError):
            await client.start()
    await client.shutdown()

    env_passed = captured.get("env")
    assert isinstance(env_passed, dict)
    assert env_passed.get("CURSOR_API_KEY") == secret

    after = dict(os.environ)
    assert after == before
    for _k, v in after.items():
        _assert_no_substring_in_text(v, secret)
    _assert_no_substring_in_text(caplog.text, secret)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_real_agent_when_enabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if os.environ.get("CURSOR_ACP_INTEGRATION") != "1":
        pytest.skip("CURSOR_ACP_INTEGRATION not set to 1")
    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        pytest.skip("CURSOR_API_KEY not set for integration")

    import shutil

    if not shutil.which("agent"):
        pytest.skip("agent binary not on PATH")

    before = dict(os.environ)
    client = CursorAcpClient(api_key=api_key, cwd=tmp_path)
    try:
        await client.start()
        await client.prompt("ping")
    finally:
        await client.shutdown()
    assert dict(os.environ) == before
