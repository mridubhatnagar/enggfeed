import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, PrimaryKeyConstraint, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from pgvector.sqlalchemy import Vector

from database import Base


class Prerequisite(Base):
    __tablename__ = "prerequisite"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=False),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    topic_name = Column(Text, nullable=False, unique=True)
    content = Column(JSONB(none_as_null=True), nullable=True)
    embedding = Column(Vector(1536), nullable=False)


class BlogPrerequisite(Base):
    __tablename__ = "blog_prerequisite"

    blog_id = Column(UUID(as_uuid=True), ForeignKey("blog.id"), nullable=False)
    prerequisite_id = Column(
        UUID(as_uuid=True), ForeignKey("prerequisite.id"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )

    __table_args__ = (PrimaryKeyConstraint("blog_id", "prerequisite_id"),)
