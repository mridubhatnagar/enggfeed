import uuid

from feedback.dao import IFeedbackDAO


class FeedbackService:
    def __init__(self, dao: IFeedbackDAO) -> None:
        self.dao = dao

    def create_feedback(
        self,
        blog_id: uuid.UUID,
        type: str,
        content: str,
        name: str | None,
        email: str | None,
    ):
        return self.dao.create(blog_id, type, content, name, email)
