"""Exception types raised by claude-crack.

These wrap the underlying ``anthropic`` SDK errors so callers embedding the
library in an app can catch ``claude_crack`` exceptions without importing the
SDK directly. The original SDK error is always preserved on ``__cause__``.
"""

from __future__ import annotations


class ClaudeCrackError(Exception):
    """Base class for all errors raised by claude-crack."""


class ConfigError(ClaudeCrackError):
    """Raised when configuration is missing or invalid (e.g. no API key)."""


class APIKeyMissingError(ConfigError):
    """Raised when no API key can be resolved from any source."""


class ClaudeAPIError(ClaudeCrackError):
    """Raised when the Claude API returns an error.

    ``status_code`` is populated when the failure was an HTTP error; it is
    ``None`` for connection/transport failures.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RefusalError(ClaudeAPIError):
    """Raised when the model declined to respond (``stop_reason == 'refusal'``).

    ``category`` carries the policy category when the API provides one.
    """

    def __init__(self, message: str, *, category: str | None = None) -> None:
        super().__init__(message)
        self.category = category
