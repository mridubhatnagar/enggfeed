import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from constants import CACHE_DEFAULT_TIMEOUT
from database import cache
from exceptions import DatabaseError
from prerequisites.models import BlogPrerequisite, Prerequisite

_KEY_PREFIX = "prerequisite_by_topic"


class IPrerequisiteDAO(ABC):
    @abstractmethod
    def get_by_topic_name(
        self, topic_name: str, use_cache: bool = True, force_update: bool = False
    ): ...

    @abstractmethod
    def list_by_ids(self, prerequisite_ids: list[uuid.UUID]): ...

    @abstractmethod
    def find_similar(
        self, embedding: list[float], threshold: float
    ) -> tuple["Prerequisite | None", "float | None"]: ...

    @abstractmethod
    def create(self, topic_name: str, embedding: list[float]): ...

    @abstractmethod
    def update(self, topic_name: str, content: dict): ...


class PrerequisiteDAO(IPrerequisiteDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    @cache.cached(timeout=CACHE_DEFAULT_TIMEOUT, key_prefix=_KEY_PREFIX)
    def get_by_topic_name(
        self, topic_name: str, use_cache: bool = True, force_update: bool = False
    ):
        try:
            return (
                self.db.query(Prerequisite)
                .filter(Prerequisite.topic_name == topic_name)
                .first()
            )
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get prerequisite by topic name: {exc}"
            ) from exc

    def list_by_ids(self, prerequisite_ids: list[uuid.UUID]) -> list:
        try:
            if not prerequisite_ids:
                return []
            return (
                self.db.query(Prerequisite)
                .filter(Prerequisite.id.in_(prerequisite_ids))
                .all()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to list prerequisites by ids: {exc}") from exc

    def find_similar(self, embedding: list[float], threshold: float) -> tuple:
        """Find the most similar prerequisite using pgvector cosine distance.

        Returns (match, score) where score is cosine similarity.
        Returns (None, score) if closest item is below threshold.
        Returns (None, None) if no existing items in DB.
        """
        try:
            result = (
                self.db.query(
                    Prerequisite,
                    (1 - Prerequisite.embedding.cosine_distance(embedding)).label(
                        "similarity"
                    ),
                )
                .order_by(Prerequisite.embedding.cosine_distance(embedding))
                .first()
            )
            if result is None:
                return (None, None)
            prereq, similarity = result
            if similarity >= threshold:
                return (prereq, float(similarity))
            return (None, float(similarity))
        except Exception as exc:
            raise DatabaseError(f"Failed to find similar prerequisite: {exc}") from exc

    def create(self, topic_name: str, embedding: list[float]) -> Prerequisite:
        try:
            prereq = Prerequisite(topic_name=topic_name, embedding=embedding)
            self.db.add(prereq)
            self.db.commit()
            self.db.refresh(prereq)
            return prereq
        except Exception as exc:
            raise DatabaseError(f"Failed to create prerequisite: {exc}") from exc

    @cache.set(key_prefix=_KEY_PREFIX, timeout=CACHE_DEFAULT_TIMEOUT, key_args=(0,))
    def update(self, topic_name: str, content: dict) -> Prerequisite | None:
        try:
            from datetime import datetime, timezone

            prereq = (
                self.db.query(Prerequisite)
                .filter(Prerequisite.topic_name == topic_name)
                .first()
            )
            if prereq is None:
                return None
            prereq.content = content
            prereq.updated_at = datetime.now(tz=timezone.utc)
            self.db.commit()
            self.db.refresh(prereq)
            return prereq
        except Exception as exc:
            raise DatabaseError(f"Failed to update prerequisite: {exc}") from exc


class IBlogPrerequisiteDAO(ABC):
    @abstractmethod
    def list_by_blog_id(self, blog_id: str): ...

    @abstractmethod
    def list_by_blog_ids(self, blog_ids: list[str]): ...

    @abstractmethod
    def create(self, blog_id: str, prerequisite_id: uuid.UUID): ...


class BlogPrerequisiteDAO(IBlogPrerequisiteDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_blog_id(self, blog_id: str) -> list:
        try:
            return (
                self.db.query(BlogPrerequisite)
                .filter(BlogPrerequisite.blog_id == blog_id)
                .all()
            )
        except Exception as exc:
            raise DatabaseError(
                f"Failed to list blog prerequisites by blog id: {exc}"
            ) from exc

    def list_by_blog_ids(self, blog_ids: list[str]) -> list:
        try:
            if not blog_ids:
                return []
            return (
                self.db.query(BlogPrerequisite)
                .filter(BlogPrerequisite.blog_id.in_(blog_ids))
                .all()
            )
        except Exception as exc:
            raise DatabaseError(
                f"Failed to list blog prerequisites by blog ids: {exc}"
            ) from exc

    def create(self, blog_id: str, prerequisite_id: uuid.UUID) -> BlogPrerequisite:
        try:
            bp = BlogPrerequisite(blog_id=blog_id, prerequisite_id=prerequisite_id)
            self.db.add(bp)
            self.db.commit()
            self.db.refresh(bp)
            return bp
        except Exception as exc:
            raise DatabaseError(f"Failed to create blog prerequisite: {exc}") from exc
