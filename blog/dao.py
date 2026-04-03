import uuid
from abc import ABC, abstractmethod

from sqlalchemy import case, func, text
from sqlalchemy.orm import Session

from blog.models import Blog, BlogSource
from constants import CONTENT_TIER_LIMITED_MAX_WORDS, CONTENT_TIER_PARTIAL_MAX_WORDS
from exceptions import DatabaseError


class IBlogSourceDAO(ABC):
    @abstractmethod
    def list_all(self): ...

    @abstractmethod
    def get_by_id(self, source_id: uuid.UUID): ...

    @abstractmethod
    def get_by_source_name(self, source: str): ...

    @abstractmethod
    def get_feed_link_by_source(self, source: str): ...


class BlogSourceDAO(IBlogSourceDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list:
        try:
            return self.db.query(BlogSource).all()
        except Exception as exc:
            raise DatabaseError(f"Failed to list blog sources: {exc}") from exc

    def get_by_id(self, source_id: uuid.UUID):
        try:
            return self.db.query(BlogSource).filter(BlogSource.id == source_id).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get blog source by id: {exc}") from exc

    def get_by_source_name(self, source: str):
        try:
            return self.db.query(BlogSource).filter(BlogSource.source == source).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get blog source by name: {exc}") from exc

    def get_feed_link_by_source(self, source: str) -> str | None:
        try:
            row = self.db.query(BlogSource).filter(BlogSource.source == source).first()
            return row.rss_feed_link if row else None
        except Exception as exc:
            raise DatabaseError(f"Failed to get feed link by source: {exc}") from exc


class IBlogDAO(ABC):
    @abstractmethod
    def get_by_id(self, blog_id: uuid.UUID): ...

    @abstractmethod
    def get_by_guid(self, guid: str): ...

    @abstractmethod
    def get_last_by_source_id(self, source_id: uuid.UUID): ...

    @abstractmethod
    def insert(self, blog): ...

    @abstractmethod
    def list_blogs(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
        page: int,
        count: int,
    ): ...

    @abstractmethod
    def count_blogs(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
    ): ...

    @abstractmethod
    def list_by_ids(self, blog_ids: list[str], page: int, count: int): ...

    @abstractmethod
    def count_by_ids(self, blog_ids: list[str]): ...


class BlogDAO(IBlogDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, blog_id: uuid.UUID):
        try:
            return self.db.query(Blog).filter(Blog.id == blog_id).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get blog by id: {exc}") from exc

    def get_by_guid(self, guid: str):
        try:
            return self.db.query(Blog).filter(Blog.guid == guid).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get blog by guid: {exc}") from exc

    def get_last_by_source_id(self, source_id: uuid.UUID):
        try:
            return (
                self.db.query(Blog)
                .filter(Blog.blog_source_id == source_id)
                .order_by(Blog.published_at.desc())
                .first()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to get last blog by source id: {exc}") from exc

    def insert(self, blog: Blog) -> None:
        try:
            self.db.add(blog)
            self.db.commit()
            self.db.refresh(blog)
        except Exception as exc:
            raise DatabaseError(f"Failed to insert blog: {exc}") from exc

    def _build_query(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
    ):
        """Build a dynamic query based on which filters are present."""
        from blog.models import Blog, BlogSource
        from tags.models import BlogTag

        query = self.db.query(Blog)

        if source_ids:
            query = query.filter(Blog.blog_source_id.in_(source_ids))

        if tag_ids:
            from sqlalchemy import select
            subquery = select(BlogTag.blog_id).where(BlogTag.tag_id.in_(tag_ids))
            query = query.filter(Blog.id.in_(subquery))

        if keyword is not None:
            # Keyword search uses PostgreSQL tsvector full-text search.
            # Excludes limited tier articles (word_count < CONTENT_TIER_LIMITED_MAX_WORDS).
            query = query.filter(Blog.word_count >= CONTENT_TIER_LIMITED_MAX_WORDS).filter(
                text(
                    "to_tsvector('english', coalesce(blog.title, '')) "
                    "@@ plainto_tsquery('english', :kw)"
                ).bindparams(kw=keyword)
            )

        return query

    def list_blogs(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
        page: int,
        count: int,
    ) -> list:
        try:
            query = self._build_query(source_ids, tag_ids, keyword)
            offset = (page - 1) * count
            if keyword is None:
                tier_order = case(
                    (Blog.word_count >= CONTENT_TIER_PARTIAL_MAX_WORDS, 0),
                    (Blog.word_count >= CONTENT_TIER_LIMITED_MAX_WORDS, 1),
                    else_=2,
                )
                query = query.order_by(tier_order, Blog.published_at.desc())
            else:
                query = query.order_by(Blog.published_at.desc())
            return query.offset(offset).limit(count).all()
        except Exception as exc:
            raise DatabaseError(f"Failed to list blogs: {exc}") from exc

    def count_blogs(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
    ) -> int:
        try:
            query = self._build_query(source_ids, tag_ids, keyword)
            return query.count()
        except Exception as exc:
            raise DatabaseError(f"Failed to count blogs: {exc}") from exc

    def list_by_ids(self, blog_ids: list[str], page: int, count: int) -> list:
        try:
            if not blog_ids:
                return []
            # Preserve the order of blog_ids (RRF order) using CASE WHEN
            order_map = {bid: idx for idx, bid in enumerate(blog_ids)}
            blogs = self.db.query(Blog).filter(Blog.id.in_(blog_ids)).all()
            # Sort by the original order
            blogs.sort(key=lambda b: order_map.get(b.id, len(blog_ids)))
            # Server-side pagination
            offset = (page - 1) * count
            return blogs[offset : offset + count]
        except Exception as exc:
            raise DatabaseError(f"Failed to list blogs by ids: {exc}") from exc

    def count_by_ids(self, blog_ids: list[str]) -> int:
        try:
            if not blog_ids:
                return 0
            return self.db.query(Blog).filter(Blog.id.in_(blog_ids)).count()
        except Exception as exc:
            raise DatabaseError(f"Failed to count blogs by ids: {exc}") from exc
