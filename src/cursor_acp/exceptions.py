"""Library errors (taxonomy root)."""


class CursorAcpError(Exception):
    """Base for ``cursor_acp`` failures."""

    pass


class CursorAcpApiKeyError(CursorAcpError):
    """Non-empty Cursor API credential required (see Cursor CLI / ACP docs for env names).

    Raised when an explicit ``api_key`` boundary value is missing or whitespace-only.
    Secrets must not appear in messages, tracebacks intentionally carry none.
    """

    pass


def validate_explicit_api_key(api_key: str) -> str:
    if not isinstance(api_key, str):
        raise CursorAcpApiKeyError("api_key must be str")
    stripped = api_key.strip()
    if not stripped:
        raise CursorAcpApiKeyError("api_key must be non-empty")
    return stripped

