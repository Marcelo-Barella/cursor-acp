from __future__ import annotations

import os

import pytest

from cursor_acp.env import (
    build_cursor_acp_subprocess_environ,
    credential_env_vars_from_cursor_docs,
)
from cursor_acp.exceptions import CursorAcpApiKeyError


def test_credential_vars_match_cursor_documentation_set() -> None:
    names = credential_env_vars_from_cursor_docs()
    assert "CURSOR_API_KEY" in names
    assert "CURSOR_AUTH_TOKEN" in names


def test_build_cursor_acp_subprocess_environ_strips_ambient_credentials() -> None:
    seed = {
        "PATH": "/bin",
        "HOME": "/tmp/h",
        "CURSOR_API_KEY": "old",
        "CURSOR_AUTH_TOKEN": "tok",
    }
    env = build_cursor_acp_subprocess_environ(api_key="new-secret", source=seed)
    assert env["CURSOR_API_KEY"] == "new-secret"
    assert "CURSOR_AUTH_TOKEN" not in env
    assert seed["CURSOR_API_KEY"] == "old"


def test_build_environ_prepends_local_bin() -> None:
    seed = {"PATH": "/usr/bin"}
    env = build_cursor_acp_subprocess_environ(
        api_key="k",
        source=seed,
        prepend_local_bin_for_agent=True,
    )
    expected_prefix = os.path.expanduser("~/.local/bin")
    assert env["PATH"].startswith(expected_prefix + os.pathsep)


def test_build_environ_validates_empty_key() -> None:
    with pytest.raises(CursorAcpApiKeyError):
        build_cursor_acp_subprocess_environ(api_key="", source={"PATH": ""})
