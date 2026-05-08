"""Cursor CLI ``agent acp`` façade: constants and stdio JSON-RPC transport."""

from cursor_acp.stdio_jsonrpc import (
    CURSOR_CLI_ACP_ARGV,
    CURSOR_CLI_ACP_EXECUTABLE,
    CursorCliAcpStdioJsonRpc,
    JSONRPC_VERSION,
    ServerRequestHandler,
)

__all__ = [
    "CURSOR_CLI_ACP_ARGV",
    "CURSOR_CLI_ACP_EXECUTABLE",
    "CursorCliAcpStdioJsonRpc",
    "JSONRPC_VERSION",
    "ServerRequestHandler",
]
