"""Cursor ACP client library.

The installable distribution is named ``cursor-acp`` (hyphenated, as used on
package indexes). The importable Python package is ``cursor_acp`` (underscore,
valid module name).
"""

from cursor_acp._meta import __version__
from cursor_acp.cursor_cli_acp import (
    CURSOR_CLI_ACP_ARGV,
    CURSOR_CLI_ACP_EXECUTABLE,
    CursorCliAcpStdioJsonRpc,
    JSONRPC_VERSION,
    ServerRequestHandler,
)
from cursor_acp.env import (
    build_cursor_acp_subprocess_environ,
    credential_env_vars_from_cursor_docs,
    default_local_agent_bin_prefix,
)
from cursor_acp.exceptions import (
    CursorAcpApiKeyError,
    CursorAcpError,
    validate_explicit_api_key,
)

__all__ = [
    "CURSOR_CLI_ACP_ARGV",
    "CURSOR_CLI_ACP_EXECUTABLE",
    "CursorAcpApiKeyError",
    "CursorAcpError",
    "CursorCliAcpStdioJsonRpc",
    "JSONRPC_VERSION",
    "ServerRequestHandler",
    "__version__",
    "build_cursor_acp_subprocess_environ",
    "credential_env_vars_from_cursor_docs",
    "default_local_agent_bin_prefix",
    "validate_explicit_api_key",
]
