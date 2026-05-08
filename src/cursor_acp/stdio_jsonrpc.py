"""Stdio newline-delimited JSON-RPC 2.0 session with ``agent acp``.

Framing, direction, and method flow follow
https://cursor.com/docs/cli/acp — re-verify after Cursor CLI upgrades.
Upstream ``github.com/azgo14/cursor-agent`` may differ; prefer tested CLI behavior.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import shutil
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from cursor_acp._meta import __version__ as _package_version
from cursor_acp.env import build_cursor_acp_subprocess_environ
from cursor_acp.exceptions import (
    CursorAcpCliNotFoundError,
    CursorAcpProtocolError,
    CursorAcpSpawnError,
    CursorAcpTimeoutError,
    json_rpc_failure,
    validate_explicit_api_key,
)

log = logging.getLogger("cursor_acp.stdio_jsonrpc")

JSONRPC_VERSION = "2.0"

CURSOR_CLI_ACP_EXECUTABLE = "agent"
CURSOR_CLI_ACP_ARGV: tuple[str, ...] = ("acp",)

ServerRequestHandler = Callable[[dict[str, Any]], Awaitable[Any]]


def _coerce_request_id_key(rid: Any) -> int | None:
    if isinstance(rid, bool):
        return None
    if isinstance(rid, int):
        return rid
    if isinstance(rid, str) and rid.isdigit():
        return int(rid)
    return None


def _summarize_argv_for_log(argv: Sequence[str]) -> str:
    out: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] in ("--api-key", "--auth-token") and i + 1 < len(argv):
            out.append(argv[i])
            out.append("<redacted>")
            i += 2
        else:
            out.append(argv[i])
            i += 1
    return " ".join(out)


class CursorCliAcpStdioJsonRpc:
    """Async subprocess transport: JSON-RPC over stdio to ``agent acp``."""

    def __init__(
        self,
        *,
        api_key: str,
        cwd: str | Path,
        executable: str = CURSOR_CLI_ACP_EXECUTABLE,
        acp_argv: Sequence[str] = CURSOR_CLI_ACP_ARGV,
        client_name: str = "cursor-acp",
        client_version: str | None = None,
        environ_base: Mapping[str, str] | None = None,
        prepend_local_bin_for_agent: bool = True,
        stderr: int | None = None,
        on_server_request: ServerRequestHandler | None = None,
        on_notification: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self._api_key = validate_explicit_api_key(api_key)
        self._cwd = Path(cwd)
        self._executable = executable
        self._acp_argv = tuple(acp_argv)
        self._client_name = client_name
        self._client_version = (
            client_version if client_version is not None else _package_version
        )
        self._environ_base = environ_base
        self._prepend_local_bin = prepend_local_bin_for_agent
        self._stderr = (
            asyncio.subprocess.DEVNULL if stderr is None else stderr
        )
        self._on_server_request = on_server_request
        self._on_notification = on_notification

        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._next_jsonrpc_id = 1
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._pending_methods: dict[int, str] = {}
        self._write_lock = asyncio.Lock()
        self._start_lock = asyncio.Lock()

    def _build_argv(self) -> list[str]:
        return [self._executable, *self._acp_argv]

    def _default_initialize_params(self) -> dict[str, Any]:
        return {
            "protocolVersion": 1,
            "clientCapabilities": {
                "fs": {"readTextFile": False, "writeTextFile": False},
                "terminal": False,
            },
            "clientInfo": {
                "name": self._client_name,
                "version": self._client_version,
            },
        }

    async def start(
        self,
        *,
        handshake_timeout: float | None = None,
        auto_initialize: bool = True,
    ) -> None:
        async with self._start_lock:
            if self._process is not None:
                if self._process.returncode is None:
                    return
                await self.aclose()

            argv = self._build_argv()
            if not shutil.which(argv[0]):
                raise CursorAcpCliNotFoundError(
                    "Cursor CLI binary not found on PATH "
                    "(see Cursor CLI ACP documentation for the expected executable)."
                )

            env = build_cursor_acp_subprocess_environ(
                api_key=self._api_key,
                source=self._environ_base,
                prepend_local_bin_for_agent=self._prepend_local_bin,
            )
            cwd_s = str(self._cwd.resolve())

            try:
                self._process = await asyncio.create_subprocess_exec(
                    *argv,
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=self._stderr,
                    cwd=cwd_s,
                    env=env,
                    limit=1024 * 1024,
                )
            except (OSError, ValueError) as e:
                raise CursorAcpSpawnError(
                    "failed to spawn Cursor CLI ACP subprocess"
                ) from e
            self._next_jsonrpc_id = 1
            self._pending.clear()
            self._pending_methods.clear()

            self._reader_task = asyncio.create_task(self._reader_loop())
            if self._stderr == asyncio.subprocess.PIPE:
                assert self._process.stderr is not None
                self._stderr_task = asyncio.create_task(self._drain_stderr())

            log.info(
                "started cursor CLI ACP subprocess",
                extra={"argv_summary": _summarize_argv_for_log(argv), "cwd": cwd_s},
            )

            try:
                if auto_initialize:
                    await self.handshake(timeout=handshake_timeout)
            except BaseException:
                await self.aclose()
                raise

    async def _drain_stderr(self) -> None:
        proc = self._process
        if proc is None or proc.stderr is None:
            return
        while True:
            line = await proc.stderr.readline()
            if not line:
                break
            log.debug("cursor agent stderr bytes=%s", len(line))

    async def handshake(
        self,
        *,
        timeout: float | None = None,
        initialize_params: dict[str, Any] | None = None,
    ) -> None:
        params = (
            self._default_initialize_params()
            if initialize_params is None
            else initialize_params
        )
        await self.request("initialize", params, timeout=timeout)
        await self.request(
            "authenticate",
            {"methodId": "cursor_login"},
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        if self._process is None or self._process.stdin is None:
            raise CursorAcpProtocolError("ACP subprocess is not running")

        async with self._write_lock:
            req_id = self._next_jsonrpc_id
            self._next_jsonrpc_id += 1
            loop = asyncio.get_running_loop()
            fut: asyncio.Future[Any] = loop.create_future()
            self._pending[req_id] = fut
            self._pending_methods[req_id] = method
            payload: dict[str, Any] = {
                "jsonrpc": JSONRPC_VERSION,
                "id": req_id,
                "method": method,
            }
            if params is not None:
                payload["params"] = params
            raw = json.dumps(payload).encode() + b"\n"
            self._process.stdin.write(raw)
            await self._process.stdin.drain()

        try:
            if timeout is not None:
                return await asyncio.wait_for(fut, timeout=timeout)
            return await fut
        except asyncio.TimeoutError as e:
            self._pending.pop(req_id, None)
            self._pending_methods.pop(req_id, None)
            if not fut.done():
                fut.cancel()
            raise CursorAcpTimeoutError("request timed out") from e
        except asyncio.CancelledError:
            self._pending.pop(req_id, None)
            self._pending_methods.pop(req_id, None)
            if not fut.done():
                fut.cancel()
            raise

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if self._process is None or self._process.stdin is None:
            raise CursorAcpProtocolError("ACP subprocess is not running")
        payload: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "method": method}
        if params is not None:
            payload["params"] = params
        raw = json.dumps(payload).encode() + b"\n"
        async with self._write_lock:
            self._process.stdin.write(raw)
            await self._process.stdin.drain()

    async def _send_raw_result(self, rpc_id: Any, result: Any) -> None:
        if self._process is None or self._process.stdin is None:
            return
        line = (
            json.dumps(
                {"jsonrpc": JSONRPC_VERSION, "id": rpc_id, "result": result}
            )
            + "\n"
        )
        async with self._write_lock:
            self._process.stdin.write(line.encode())
            await self._process.stdin.drain()

    async def _send_raw_error(
        self, rpc_id: Any, *, code: int, message: str
    ) -> None:
        if self._process is None or self._process.stdin is None:
            return
        line = (
            json.dumps(
                {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": rpc_id,
                    "error": {"code": code, "message": message},
                }
            )
            + "\n"
        )
        async with self._write_lock:
            self._process.stdin.write(line.encode())
            await self._process.stdin.drain()

    async def _handle_server_request(self, msg: dict[str, Any]) -> None:
        mid = msg.get("id")
        method = msg.get("method")
        if mid is None or method is None:
            return
        try:
            if self._on_server_request is not None:
                result = await self._on_server_request(msg)
            elif method == "session/request_permission":
                result = {
                    "outcome": {
                        "outcome": "selected",
                        "optionId": "allow-once",
                    }
                }
            else:
                log.warning(
                    "unhandled ACP server request",
                    extra={"method": method, "rpc_id_type": type(mid).__name__},
                )
                await self._send_raw_error(
                    mid,
                    code=-32601,
                    message="Method not handled by client",
                )
                return
            await self._send_raw_result(mid, result)
        except asyncio.CancelledError:
            raise
        except BaseException:
            log.exception("server request handler failed")
            await self._send_raw_error(
                mid, code=-32603, message="Internal error"
            )

    async def _handle_notification(self, msg: dict[str, Any]) -> None:
        if self._on_notification is not None:
            await self._on_notification(msg)

    async def _dispatch_line(self, msg: dict[str, Any]) -> None:
        if msg.get("jsonrpc") != JSONRPC_VERSION:
            return

        mid = msg.get("id")
        if mid is not None and ("result" in msg or "error" in msg):
            key = _coerce_request_id_key(mid)
            if key is None:
                return
            fut = self._pending.pop(key, None)
            method_name = self._pending_methods.pop(key, "unknown")
            if fut is None:
                return
            if "error" in msg:
                err = msg["error"]
                if isinstance(err, dict):
                    fut.set_exception(json_rpc_failure(method_name, err))
                else:
                    fut.set_exception(
                        CursorAcpProtocolError("JSON-RPC error payload was not an object")
                    )
            else:
                fut.set_result(msg.get("result"))
            return

        method = msg.get("method")
        if method is None:
            return

        if "id" not in msg:
            await self._handle_notification(msg)
            return

        await self._handle_server_request(msg)

    async def _reader_loop(self) -> None:
        assert self._process is not None and self._process.stdout is not None
        proc = self._process
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                try:
                    msg = json.loads(line.decode())
                except json.JSONDecodeError:
                    log.warning("non-json stdout line discarded")
                    continue
                if not isinstance(msg, dict):
                    continue
                try:
                    await self._dispatch_line(msg)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("message dispatch failed")
        finally:
            await self._fail_all_pending(
                CursorAcpProtocolError("ACP stdout closed")
            )

    async def _fail_all_pending(self, exc: BaseException) -> None:
        pending = list(self._pending.items())
        self._pending.clear()
        self._pending_methods.clear()
        for _, fut in pending:
            if not fut.done():
                try:
                    fut.set_exception(exc)
                except (asyncio.InvalidStateError, RuntimeError):
                    pass

    async def aclose(self) -> None:
        if (
            self._process is None
            and self._reader_task is None
            and self._stderr_task is None
        ):
            return
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            try:
                await self._stderr_task
            except asyncio.CancelledError:
                pass
            self._stderr_task = None
        proc = self._process
        self._process = None
        if proc is not None:
            if proc.stdin and not proc.stdin.is_closing():
                proc.stdin.close()
                with contextlib.suppress(Exception):
                    await proc.stdin.wait_closed()
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    proc.kill()
                    with contextlib.suppress(ProcessLookupError):
                        await proc.wait()
        await self._fail_all_pending(
            CursorAcpProtocolError("ACP transport closed")
        )

    async def __aenter__(self) -> CursorCliAcpStdioJsonRpc:
        await self.start()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


