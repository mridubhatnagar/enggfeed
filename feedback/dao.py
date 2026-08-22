import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from exceptions import DatabaseError
from feedback.models import Feedback


class IFeedbackDAO(ABC):
    @abstractmethod
    def create(
        self,
        blog_id: uuid.UUID,
        type: str,
        content: str,
        name: str | None,
        email: str | None,
    ): ...


class FeedbackDAO(IFeedbackDAO):
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        blog_id: uuid.UUID,
        type: str,
        content: str,
        name: str | None,
        email: str | None,
    ) -> Feedback:
        try:
            feedback = Feedback(
                blog_id=blog_id, type=type, content=content, name=name, email=email
            )
            self.db.add(feedback)
            self.db.commit()
            self.db.refresh(feedback)
            return feedback
        except Exception as exc:
            raise DatabaseError(f"Failed to create feedback: {exc}") from exc
