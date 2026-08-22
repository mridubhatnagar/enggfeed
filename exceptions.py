class DatabaseError(Exception):
    """Raised by the DAO layer when a SQLAlchemy exception is caught."""


class ForbiddenError(Exception):
    """Raised when a content tier check fails."""


class NotFoundError(Exception):
    """Raised when a requested record is not found."""


class RSSFeedError(Exception):
    """Raised when an RSS feed is unavailable."""


class LLMUnreachableError(Exception):
    """Raised when an LLM call fails, times out, or returns invalid JSON."""


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""


class ValidationError(Exception):
    """Raised when request content fails server-side validation."""


class FeedbackError(Exception):
    """Raised when feedback submission fails due to an unexpected error."""
