import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID

from database import Base


class BlogSource(Base):
    __tablename__ = "blog_source"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    rss_feed_link = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)


class Blog(Base):
    __tablename__ = "blog"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guid = Column(Text, nullable=False, unique=True)  # RSS guid — used for dedup on ingest
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    link = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    thumbnail = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=False)
    published_at = Column(DateTime(timezone=False), nullable=False)
    blog_source_id = Column(UUID(as_uuid=True), ForeignKey("blog_source.id"), nullable=False)
