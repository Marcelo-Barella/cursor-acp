"""Stable v1 façade for Cursor CLI ACP over stdio JSON-RPC.

Event streaming for model output is intentionally out of scope for v1; a future
``stream_prompt`` (or notification subscription API) may be added without breaking
the core ``prompt`` contract.

Transport and method flow follow https://cursor.com/docs/cli/acp and ACP
``session/prompt`` results include ``stopReason`` per the Agent Client Protocol
prompt turn documentation.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict, cast

from cursor_acp.exceptions import (
    CursorAcpCancelledError,
    CursorAcpProtocolError,
    validate_explicit_api_key,
)
from cursor_acp.stdio_jsonrpc import (
    CURSOR_CLI_ACP_ARGV,
    CURSOR_CLI_ACP_EXECUTABLE,
    CursorCliAcpStdioJsonRpc,
    ServerRequestHandler,
)


class PromptResult(TypedDict):
    """JSON-RPC ``result`` object for ``session/prompt`` (ACP prompt turn)."""

    stopReason: str


class CursorAcpClient:
    def __init__(
        self,
        api_key: str,
        cwd: Path,
        *,
        cli_executable: str | None = None,
        acp_argv: Sequence[str] = CURSOR_CLI_ACP_ARGV,
        client_name: str = "cursor-acp",
        client_version: str | None = None,
        environ_base: Mapping[str, str] | None = None,
        prepend_local_bin_for_agent: bool = True,
        stderr: int | None = None,
        on_server_request: ServerRequestHandler | None = None,
        on_notification: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        mcp_servers: Sequence[dict[str, Any]] | None = None,
        handshake_timeout: float | None = None,
        request_timeout: float | None = None,
        session_new_timeout: float | None = None,
    ) -> None:
        self._api_key = validate_explicit_api_key(api_key)
        self._cwd = Path(cwd)
        self._cli_executable = (
            cli_executable
            if cli_executable is not None
            else CURSOR_CLI_ACP_EXECUTABLE
        )
        self._acp_argv = acp_argv
        self._client_name = client_name
        self._client_version = client_version
        self._environ_base = environ_base
        self._prepend_local_bin = prepend_local_bin_for_agent
        self._stderr = stderr
        self._on_server_request = on_server_request
        self._on_notification = on_notification
        self._mcp_servers = (
            list(mcp_servers) if mcp_servers is not None else []
        )
        self._handshake_timeout = handshake_timeout
        self._default_request_timeout = request_timeout
        self._session_new_timeout = session_new_timeout

        self._rpc: CursorCliAcpStdioJsonRpc | None = None
        self._session_id: str | None = None

    def _session_timeout(self) -> float | None:
        if self._session_new_timeout is not None:
            return self._session_new_timeout
        return self._default_request_timeout

    def _make_rpc(self) -> CursorCliAcpStdioJsonRpc:
        return CursorCliAcpStdioJsonRpc(
            api_key=self._api_key,
            cwd=self._cwd,
            executable=self._cli_executable,
            acp_argv=self._acp_argv,
            client_name=self._client_name,
            client_version=self._client_version,
            environ_base=self._environ_base,
            prepend_local_bin_for_agent=self._prepend_local_bin,
            stderr=self._stderr,
            on_server_request=self._on_server_request,
            on_notification=self._on_notification,
        )

    async def start(self) -> None:
        if self._rpc is not None:
            return
        rpc = self._make_rpc()
        try:
            await rpc.start(
                handshake_timeout=self._handshake_timeout,
                auto_initialize=True,
            )
            raw = await rpc.request(
                "session/new",
                {
                    "cwd": str(self._cwd.resolve()),
                    "mcpServers": self._mcp_servers,
                },
                timeout=self._session_timeout(),
            )
            if not isinstance(raw, dict):
                raise CursorAcpProtocolError("session/new result was not an object")
            sid = raw.get("sessionId")
            if not isinstance(sid, str) or not sid:
                raise CursorAcpProtocolError("session/new result missing sessionId")
            self._rpc = rpc
            self._session_id = sid
        except BaseException:
            await rpc.aclose()
            raise

    async def shutdown(self) -> None:
        rpc = self._rpc
        self._rpc = None
        self._session_id = None
        if rpc is not None:
            await rpc.aclose()

    async def prompt(
        self,
        text: str,
        *,
        timeout: float | None = None,
    ) -> PromptResult:
        await self.start()
        assert self._rpc is not None and self._session_id is not None
        t = self._default_request_timeout if timeout is None else timeout
        try:
            raw = await self._rpc.request(
                "session/prompt",
                {
                    "sessionId": self._session_id,
                    "prompt": [{"type": "text", "text": text}],
                },
                timeout=t,
            )
        except asyncio.CancelledError as exc:
            raise CursorAcpCancelledError() from exc
        if not isinstance(raw, dict):
            raise CursorAcpProtocolError("session/prompt result was not an object")
        if "stopReason" not in raw:
            raise CursorAcpProtocolError("session/prompt result missing stopReason")
        sr = raw.get("stopReason")
        if not isinstance(sr, str):
            raise CursorAcpProtocolError("session/prompt stopReason was not a string")
        return cast(PromptResult, raw)

    async def __aenter__(self) -> CursorAcpClient:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.shutdown()
