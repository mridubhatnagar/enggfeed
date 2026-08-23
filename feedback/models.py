import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blog_id = Column(UUID(as_uuid=True), ForeignKey("blog.id"), nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(tz=timezone.utc), nullable=False
    )
