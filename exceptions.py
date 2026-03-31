class DatabaseError(Exception):
    """Raised by the DAO layer when a SQLAlchemy exception is caught."""


class UnauthorizedError(Exception):
    """Raised when no valid JWT is present."""


class AuthError(Exception):
    """Raised on OAuth flow failure (bad state, token exchange error, etc.)."""


class NotAllowedError(AuthError):
    """Raised when an authenticated user's email is not in the allowlist."""


class ForbiddenError(Exception):
    """Raised when a content tier check fails."""


class NotFoundError(Exception):
    """Raised when a requested record is not found."""


class RSSFeedError(Exception):
    """Raised when an RSS feed is unavailable."""


class LLMUnreachableError(Exception):
    """Raised when an LLM call fails, times out, or returns invalid JSON."""
