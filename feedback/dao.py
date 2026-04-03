import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from exceptions import DatabaseError
from feedback.models import Feedback


class IFeedbackDAO(ABC):
    @abstractmethod
    def get_by_user_blog_type(self, user_id: uuid.UUID, blog_id: uuid.UUID, type: str): ...

    @abstractmethod
    def create(self, blog_id: uuid.UUID, user_id: uuid.UUID, type: str, content: str): ...

    @abstractmethod
    def update(self, user_id: uuid.UUID, blog_id: uuid.UUID, type: str, content: str): ...


class FeedbackDAO(IFeedbackDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_blog_type(self, user_id: uuid.UUID, blog_id: uuid.UUID, type: str):
        try:
            return (
                self.db.query(Feedback)
                .filter(
                    Feedback.user_id == user_id,
                    Feedback.blog_id == blog_id,
                    Feedback.type == type,
                )
                .first()
            )
        except Exception as exc:
            raise DatabaseError(f"Failed to get feedback: {exc}") from exc

    def create(self, blog_id: uuid.UUID, user_id: uuid.UUID, type: str, content: str) -> Feedback:
        try:
            feedback = Feedback(blog_id=blog_id, user_id=user_id, type=type, content=content)
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            return feedback
        except Exception as exc:
            raise DatabaseError(f"Failed to create feedback: {exc}") from exc

    def update(self, user_id: uuid.UUID, blog_id: uuid.UUID, type: str, content: str) -> Feedback:
        try:
            feedback = (
                self.db.query(Feedback)
                .filter(
                    Feedback.user_id == user_id,
                    Feedback.blog_id == blog_id,
                    Feedback.type == type,
                )
                .first()
            )
            feedback.content = content
            self.db.commit()
            self.db.refresh(feedback)
            return feedback
        except Exception as exc:
            raise DatabaseError(f"Failed to update feedback: {exc}") from exc
