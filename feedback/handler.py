import uuid
from datetime import datetime, timezone

from auth.utils import decode_jwt_token
from constants import (
    FEEDBACK_MAX_LENGTH,
    FEEDBACK_MIN_LENGTH,
    FEEDBACK_RATE_LIMIT_PER_DAY,
    FEEDBACK_RATE_LIMIT_PER_MINUTE,
)
from database import cache
from exceptions import FeedbackError, RateLimitError, UnauthorizedError, ValidationError
from feedback.enums import FeedbackType
from feedback.service import FeedbackService
from schemas import APIResponse


class FeedbackHandler:
    def __init__(self, feedback_service: FeedbackService) -> None:
        self.feedback_service = feedback_service

    def submit_feedback(
        self, blog_id: uuid.UUID, type: FeedbackType, content: str, token: str | None
    ) -> APIResponse:
        if not token:
            raise UnauthorizedError("Authentication required")
        payload = decode_jwt_token(token)
        user_id = uuid.UUID(payload["user_id"])

        now = datetime.now(tz=timezone.utc)
        try:
            minute_key = f"feedback:{user_id}:minute:{now.strftime('%Y%m%d%H%M')}"
            minute_count = cache._client.incr(minute_key)
            if minute_count == 1:
                cache._client.expire(minute_key, 60)
            if minute_count > FEEDBACK_RATE_LIMIT_PER_MINUTE:
                raise RateLimitError("Rate limit exceeded: too many requests per minute")

            day_key = f"feedback:{user_id}:{now.strftime('%Y%m%d')}"
            day_count = cache._client.incr(day_key)
            if day_count == 1:
                cache._client.expire(day_key, 86400)
            if day_count > FEEDBACK_RATE_LIMIT_PER_DAY:
                raise RateLimitError("Rate limit exceeded: too many requests today")
        except RateLimitError:
            raise
        except Exception as exc:
            raise FeedbackError("Sorry, your feedback couldn't be processed. Please try again later.") from exc

        content = content.strip()
        if not content:
            return APIResponse(success=True, data=None, error=None)

        if len(content) < FEEDBACK_MIN_LENGTH or len(content) > FEEDBACK_MAX_LENGTH:
            raise ValidationError(
                f"Feedback must be between {FEEDBACK_MIN_LENGTH} and {FEEDBACK_MAX_LENGTH} characters"
            )

        self.feedback_service.create_or_update(user_id, blog_id, type, content)
        return APIResponse(success=True, data=None, error=None)
