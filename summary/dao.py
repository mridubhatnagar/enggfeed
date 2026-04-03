from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy.orm import Session

from database import _DEFAULT_TIMEOUT, cache
from exceptions import DatabaseError
from summary.models import Summary

_KEY_PREFIX = "summary_by_blog"


class ISummaryDAO(ABC):
    @abstractmethod
    def get_by_blog_id(self, blog_id: str, use_cache: bool = True, force_update: bool = False): ...

    @abstractmethod
    def create(self, blog_id: str, content: dict): ...

    @abstractmethod
    def update(self, blog_id: str, content: dict): ...


class SummaryDAO(ISummaryDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    @cache.cached(timeout=_DEFAULT_TIMEOUT, key_prefix=_KEY_PREFIX)
    def get_by_blog_id(self, blog_id: str, use_cache: bool = True, force_update: bool = False):
        try:
            return self.db.query(Summary).filter(Summary.blog_id == blog_id).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get summary by blog_id: {exc}") from exc

    @cache.set(key_prefix=_KEY_PREFIX, timeout=_DEFAULT_TIMEOUT, key_args=(0,))
    def create(self, blog_id: str, content: dict) -> Summary:
        try:
            row = Summary(blog_id=blog_id, content=content)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return row
        except Exception as exc:
            raise DatabaseError(f"Failed to create summary: {exc}") from exc

    @cache.set(key_prefix=_KEY_PREFIX, timeout=_DEFAULT_TIMEOUT, key_args=(0,))
    def update(self, blog_id: str, content: dict) -> Summary:
        try:
            row = self.db.query(Summary).filter(Summary.blog_id == blog_id).first()
            if row is None:
                raise DatabaseError(f"Summary row not found for blog_id: {blog_id}")
            row.content = content
            row.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            return row
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Failed to update summary: {exc}") from exc
