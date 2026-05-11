from __future__ import annotations

import pytest

from cursor_acp.exceptions import CursorAcpApiKeyError, validate_explicit_api_key


def test_validate_explicit_api_key_rejects_blank() -> None:
    with pytest.raises(CursorAcpApiKeyError):
        validate_explicit_api_key("")
    with pytest.raises(CursorAcpApiKeyError):
        validate_explicit_api_key("   ")
    with pytest.raises(CursorAcpApiKeyError):
        validate_explicit_api_key("\t")


def test_validate_explicit_api_key_rejects_non_string() -> None:
    with pytest.raises(CursorAcpApiKeyError):
        validate_explicit_api_key(None)  # type: ignore[arg-type]


def test_validate_explicit_api_key_returns_stripped() -> None:
    assert validate_explicit_api_key(" abc ") == "abc"
