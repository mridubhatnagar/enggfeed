import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class Simplify(Base):
    __tablename__ = "simplify"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    blog_id = Column(UUID(as_uuid=True), ForeignKey("blog.id"), nullable=False)
    simplify = Column(Text, nullable=False)
