"""Cursor ACP client library.

The installable distribution is named ``pycursor-acp`` (hyphenated, as used on
package indexes). The importable Python package is ``cursor_acp`` (underscore,
valid module name).
"""

from cursor_acp._meta import __version__
from cursor_acp.client import CursorAcpClient, CursorAcpInteractionMode, PromptResult
from cursor_acp.cursor_cli_acp import (
    CURSOR_CLI_ACP_ARGV,
    CURSOR_CLI_ACP_EXECUTABLE,
    JSONRPC_VERSION,
    CursorCliAcpStdioJsonRpc,
    ServerRequestHandler,
)
from cursor_acp.env import (
    build_cursor_acp_subprocess_environ,
    credential_env_vars_from_cursor_docs,
    default_local_agent_bin_prefix,
)
from cursor_acp.exceptions import (
    CursorAcpApiKeyError,
    CursorAcpAuthError,
    CursorAcpCancelledError,
    CursorAcpCliNotFoundError,
    CursorAcpError,
    CursorAcpProtocolError,
    CursorAcpSessionError,
    CursorAcpSpawnError,
    CursorAcpTimeoutError,
    validate_explicit_api_key,
)

__all__ = [
    "CURSOR_CLI_ACP_ARGV",
    "CURSOR_CLI_ACP_EXECUTABLE",
    "CursorAcpApiKeyError",
    "CursorAcpAuthError",
    "CursorAcpCancelledError",
    "CursorAcpCliNotFoundError",
    "CursorAcpClient",
    "CursorAcpError",
    "CursorAcpInteractionMode",
    "CursorAcpProtocolError",
    "CursorAcpSessionError",
    "CursorAcpSpawnError",
    "CursorAcpTimeoutError",
    "CursorCliAcpStdioJsonRpc",
    "JSONRPC_VERSION",
    "PromptResult",
    "ServerRequestHandler",
    "__version__",
    "build_cursor_acp_subprocess_environ",
    "credential_env_vars_from_cursor_docs",
    "default_local_agent_bin_prefix",
    "validate_explicit_api_key",
]
