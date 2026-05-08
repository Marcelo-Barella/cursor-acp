from __future__ import annotations

import os

from cursor_acp.env import build_cursor_acp_subprocess_environ


def test_build_cursor_acp_environ_does_not_mutate_os_environ() -> None:
    marker = "CURSOR_API_KEY"
    previous = os.environ.get(marker)
    try:
        os.environ[marker] = "ambient-token"
        env = build_cursor_acp_subprocess_environ(api_key="explicit-key")
        assert env["CURSOR_API_KEY"] == "explicit-key"
        assert os.environ[marker] == "ambient-token"
    finally:
        if previous is None:
            os.environ.pop(marker, None)
        else:
            os.environ[marker] = previous
