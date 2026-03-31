import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID

from database import Base


class Summary(Base):
    __tablename__ = "summary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    blog_id = Column(UUID(as_uuid=True), ForeignKey("blog.id"), nullable=False)
    content = Column(JSONB, nullable=False)
