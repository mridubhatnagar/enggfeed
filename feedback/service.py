import uuid

from feedback.dao import IFeedbackDAO


class FeedbackService:
    def __init__(self, dao: IFeedbackDAO) -> None:
        self.dao = dao

    def get_feedback_by_user_blog_type(self, user_id: uuid.UUID, blog_id: uuid.UUID, type: str):
        return self.dao.get_by_user_blog_type(user_id, blog_id, type)

    def create_feedback(self, blog_id: uuid.UUID, user_id: uuid.UUID, type: str, content: str):
        return self.dao.create(blog_id, user_id, type, content)

    def update_feedback(self, feedback, content: str):
        return self.dao.update(feedback, content)

    def create_or_update(self, user_id: uuid.UUID, blog_id: uuid.UUID, type: str, content: str):
        existing = self.get_feedback_by_user_blog_type(user_id, blog_id, type)
        if existing:
            return self.update_feedback(existing, content)
        return self.create_feedback(blog_id, user_id, type, content)
