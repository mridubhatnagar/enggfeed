import uuid
from abc import ABC, abstractmethod

from sqlalchemy import func
from sqlalchemy.orm import Session

from exceptions import DatabaseError
from tags.models import BlogTag, Tag


class ITagDAO(ABC):
    @abstractmethod
    def list_by_ids(self, tag_ids: list[uuid.UUID]): ...

    @abstractmethod
    def list_all_with_counts(self): ...

    @abstractmethod
    def get_by_name(self, name: str): ...

    @abstractmethod
    def find_similar(
        self, embedding: list[float], threshold: float
    ) -> tuple["Tag | None", "float | None"]: ...

    @abstractmethod
    def create(self, name: str, embedding: list[float]): ...


class TagDAO(ITagDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_ids(self, tag_ids: list[uuid.UUID]) -> list:
        try:
            if not tag_ids:
                return []
            return self.db.query(Tag).filter(Tag.tag_id.in_(tag_ids)).all()
        except Exception as exc:
            raise DatabaseError(f"Failed to list tags by ids: {exc}") from exc

    def list_all_with_counts(self) -> list:
        try:
            return (
                self.db.query(Tag, func.count(BlogTag.blog_id).label("count"))
                .join(BlogTag, Tag.tag_id == BlogTag.tag_id)
                .group_by(Tag.tag_id)
                .order_by(func.count(BlogTag.blog_id).desc())
                .all()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to list tags with counts: {exc}") from exc

    def get_by_name(self, name: str):
        try:
            return self.db.query(Tag).filter(Tag.tag == name).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get tag by name: {exc}") from exc

    def find_similar(
        self, embedding: list[float], threshold: float
    ) -> tuple:
        """Find the most similar tag using pgvector cosine distance.

        Returns (match, score) where score is cosine similarity.
        Returns (None, score) if closest item is below threshold.
        Returns (None, None) if no existing items in DB.
        """
        try:
            # cosine distance = 1 - cosine similarity
            # <=> operator returns cosine distance
            result = (
                self.db.query(Tag, (1 - Tag.embedding.cosine_distance(embedding)).label("similarity"))
                .order_by(Tag.embedding.cosine_distance(embedding))
                .first()
            )
            if result is None:
                return (None, None)
            tag, similarity = result
            if similarity >= threshold:
                return (tag, float(similarity))
            return (None, float(similarity))
        except Exception as exc:
            raise DatabaseError(f"Failed to find similar tag: {exc}") from exc

    def create(self, name: str, embedding: list[float]) -> Tag:
        try:
            tag = Tag(tag=name, embedding=embedding)
            self.db.add(tag)
            self.db.commit()
            self.db.refresh(tag)
            return tag
        except Exception as exc:
            raise DatabaseError(f"Failed to create tag: {exc}") from exc


class IBlogTagDAO(ABC):
    @abstractmethod
    def list_by_blog_id(self, blog_id: str): ...

    @abstractmethod
    def list_by_blog_ids(self, blog_ids: list[str]): ...

    @abstractmethod
    def list_by_tag_id(self, tag_id: uuid.UUID): ...

    @abstractmethod
    def create(self, blog_id: str, tag_id: uuid.UUID): ...


class BlogTagDAO(IBlogTagDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_blog_id(self, blog_id: str) -> list:
        try:
            return self.db.query(BlogTag).filter(BlogTag.blog_id == blog_id).all()
        except Exception as exc:
            raise DatabaseError(f"Failed to list blog tags by blog id: {exc}") from exc

    def list_by_blog_ids(self, blog_ids: list[str]) -> list:
        try:
            if not blog_ids:
                return []
            return self.db.query(BlogTag).filter(BlogTag.blog_id.in_(blog_ids)).all()
        except Exception as exc:
            raise DatabaseError(f"Failed to list blog tags by blog ids: {exc}") from exc

    def list_by_tag_id(self, tag_id: uuid.UUID) -> list:
        try:
            return self.db.query(BlogTag).filter(BlogTag.tag_id == tag_id).all()
        except Exception as exc:
            raise DatabaseError(f"Failed to list blog tags by tag id: {exc}") from exc

    def create(self, blog_id: str, tag_id: uuid.UUID) -> BlogTag:
        try:
            blog_tag = BlogTag(blog_id=blog_id, tag_id=tag_id)
            self.db.add(blog_tag)
            self.db.commit()
            self.db.refresh(blog_tag)
            return blog_tag
        except Exception as exc:
            raise DatabaseError(f"Failed to create blog tag: {exc}") from exc
