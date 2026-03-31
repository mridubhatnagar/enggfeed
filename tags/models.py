import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from database import Base


class Tag(Base):
    __tablename__ = "tag"

    tag_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    tag = Column(Text, nullable=False, unique=True)
    embedding = Column(Vector(1536), nullable=False)


class BlogTag(Base):
    __tablename__ = "blog_tag"

    blog_id = Column(UUID(as_uuid=True), ForeignKey("blog.id"), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey("tag.tag_id"), nullable=False)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    __table_args__ = (PrimaryKeyConstraint("blog_id", "tag_id"),)
