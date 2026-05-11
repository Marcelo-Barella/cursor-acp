"""Library errors (taxonomy root)."""

import asyncio
from collections.abc import Mapping
from typing import Any


class CursorAcpError(Exception):
    """Base for ``cursor_acp`` failures."""

    def __repr__(self) -> str:
        if not self.args:
            return type(self).__name__
        return f"{type(self).__name__}({self.args[0]!r})"


class CursorAcpApiKeyError(CursorAcpError):
    """Non-empty Cursor API credential (see Cursor CLI / ACP docs for env names).

    Raised when an explicit ``api_key`` boundary value is missing or whitespace-only.
    Secrets must not appear in messages, tracebacks intentionally carry none.
    """

    pass


class CursorAcpCliNotFoundError(CursorAcpError):
    """Configured Cursor CLI executable is missing (not resolvable on PATH)."""

    pass


class CursorAcpSpawnError(CursorAcpError):
    """Subprocess spawn or startup failed before a stable stdio session exists."""

    pass


class CursorAcpProtocolError(CursorAcpError):
    """Transport/protocol failure (framing, JSON-RPC envelope, or unexpected I/O)."""

    pass


class CursorAcpAuthError(CursorAcpError):
    """JSON-RPC failure during ACP handshake (``initialize`` / ``authenticate``)."""

    pass


class CursorAcpSessionError(CursorAcpError):
    """JSON-RPC failure during session lifecycle calls (for example ``session/*``)."""

    pass


class CursorAcpTimeoutError(CursorAcpError):
    """A request exceeded its deadline."""

    pass


class CursorAcpCancelledError(CursorAcpError, asyncio.CancelledError):
    """An operation was cancelled (task cancellation or client abort)."""

    def __init__(self, message: str = "operation cancelled") -> None:
        CursorAcpError.__init__(self, message)


def validate_explicit_api_key(api_key: str) -> str:
    if not isinstance(api_key, str):
        raise CursorAcpApiKeyError("api_key must be str")
    stripped = api_key.strip()
    if not stripped:
        raise CursorAcpApiKeyError("api_key must be non-empty")
    return stripped


def json_rpc_failure(
    method: str, err: Mapping[str, Any]
) -> CursorAcpAuthError | CursorAcpSessionError | CursorAcpProtocolError:
    code = err.get("code")
    if method in ("initialize", "authenticate"):
        return CursorAcpAuthError(f"{method} failed (code={code!r})")
    if method.startswith("session/"):
        return CursorAcpSessionError(f"{method} failed (code={code!r})")
    return CursorAcpProtocolError(f"JSON-RPC error (method={method!r}, code={code!r})")
