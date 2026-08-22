import uuid

from pydantic import BaseModel, Field

from feedback.enums import FeedbackType


class FeedbackRequest(BaseModel):
    blog_id: uuid.UUID
    type: FeedbackType
    content: str = Field(max_length=500)
    name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)
