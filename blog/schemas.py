import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ContentTier(str, Enum):
    LIMITED = "LIMITED"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class BlogItem(BaseModel):
    created_at: datetime
    link: str
    title: str
    thumbnail: str | None
    word_count: int
    published_at: datetime | None
    blog_source_id: uuid.UUID
    source: str
    tags: list[str]
    prerequisites: list[str]
    content_tier: ContentTier


class PaginatedBlogs(BaseModel):
    total: int
    page: int
    count: int
    total_pages: int
    blogs: dict[str, BlogItem]


class BlogSource(BaseModel):
    id: uuid.UUID
    source: str


class TagWithCount(BaseModel):
    tag: str
    count: int
