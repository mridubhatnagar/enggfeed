import uuid

from pydantic import BaseModel, Field

from feedback.enums import FeedbackType


class FeedbackRequest(BaseModel):
    blog_id: uuid.UUID
    type: FeedbackType
    content: str = Field(max_length=500)
