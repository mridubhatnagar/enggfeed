from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy.orm import Session

from database import _DEFAULT_TIMEOUT, cache
from exceptions import DatabaseError
from simplify.models import Simplify

_KEY_PREFIX = "simplify_by_blog"


class ISimplifyDAO(ABC):
    @abstractmethod
    def get_by_blog_id(self, blog_id: str, use_cache: bool = True, force_update: bool = False): ...

    @abstractmethod
    def create(self, blog_id: str, simplify: str): ...

    @abstractmethod
    def update(self, blog_id: str, simplify: str): ...


class SimplifyDAO(ISimplifyDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    @cache.cached(timeout=_DEFAULT_TIMEOUT, key_prefix=_KEY_PREFIX)
    def get_by_blog_id(self, blog_id: str, use_cache: bool = True, force_update: bool = False):
        try:
            return self.db.query(Simplify).filter(Simplify.blog_id == blog_id).first()
        except Exception as exc:
            raise DatabaseError(f"Failed to get simplify by blog_id: {exc}") from exc

    @cache.set(key_prefix=_KEY_PREFIX, timeout=_DEFAULT_TIMEOUT, key_args=(0,))
    def create(self, blog_id: str, simplify: str) -> Simplify:
        try:
            row = Simplify(blog_id=blog_id, simplify=simplify)
            self.db.add(row)
            self.db.commit()
            self.db.refresh(row)
            return row
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to create simplify: {exc}") from exc

    @cache.set(key_prefix=_KEY_PREFIX, timeout=_DEFAULT_TIMEOUT, key_args=(0,))
    def update(self, blog_id: str, simplify: str) -> Simplify:
        try:
            row = self.db.query(Simplify).filter(Simplify.blog_id == blog_id).first()
            if row is None:
                raise DatabaseError(f"Simplify row not found for blog_id: {blog_id}")
            row.simplify = simplify
            row.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(row)
            return row
        except DatabaseError:
            raise
        except Exception as exc:
            self.db.rollback()
            raise DatabaseError(f"Failed to update simplify: {exc}") from exc
