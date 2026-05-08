"""Subprocess environments for Cursor CLI ACP mode.

Credential variable names CURSOR_API_KEY / CURSOR_AUTH_TOKEN are documented at
https://cursor.com/docs/cli/acp — re-verify on Cursor CLI upgrades.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

from cursor_acp.exceptions import validate_explicit_api_key


def credential_env_vars_from_cursor_docs() -> frozenset[str]:
    """Names referenced by official Cursor CLI ACP docs for subprocess auth."""

    return frozenset({"CURSOR_API_KEY", "CURSOR_AUTH_TOKEN"})


def default_local_agent_bin_prefix() -> str:
    """Common install path for the ``agent`` binary (often added to PATH manually)."""

    return os.path.expanduser("~/.local/bin")


def build_cursor_acp_subprocess_environ(
    *,
    api_key: str,
    source: Mapping[str, str] | None = None,
    prepend_local_bin_for_agent: bool = True,
) -> dict[str, str]:
    """Build an isolated env dict for ``agent acp`` without mutating ``os.environ``.

    Inherits keys from ``source`` (default: snapshot ``dict(os.environ)``), strips
    documented Cursor credential env entries so callers are not ambiguous, then sets
    ``CURSOR_API_KEY`` from the explicit ``api_key`` argument (validated caller-side).
    """
    secret = validate_explicit_api_key(api_key)

    env = dict(os.environ if source is None else source)
    for name in credential_env_vars_from_cursor_docs():
        env.pop(name, None)
    env["CURSOR_API_KEY"] = secret
    if prepend_local_bin_for_agent:
        lb = default_local_agent_bin_prefix()
        if lb:
            path = env.get("PATH", "")
            parts = path.split(os.pathsep) if path else []
            if lb not in parts:
                env["PATH"] = lb + os.pathsep + path if path else lb
    return env
