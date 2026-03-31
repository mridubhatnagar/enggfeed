import uuid

from prerequisites.dao import IBlogPrerequisiteDAO, IPrerequisiteDAO


class PrerequisiteService:
    def __init__(self, dao: IPrerequisiteDAO) -> None:
        self.dao = dao

    def get_prerequisite_by_topic_name(self, topic_name: str, use_cache: bool = True, force_update: bool = False):
        return self.dao.get_by_topic_name(topic_name, use_cache=use_cache, force_update=force_update)

    def list_prerequisites_by_ids(self, prerequisite_ids: list[uuid.UUID]) -> list:
        return self.dao.list_by_ids(prerequisite_ids)

    def find_similar_prerequisite(self, embedding: list[float], threshold: float) -> tuple:
        return self.dao.find_similar(embedding, threshold)

    def create_prerequisite(self, topic_name: str, embedding: list[float]):
        return self.dao.create(topic_name, embedding)

    def update_prerequisite(self, topic_name: str, content: dict):
        return self.dao.update(topic_name, content)


class BlogPrerequisiteService:
    def __init__(self, dao: IBlogPrerequisiteDAO) -> None:
        self.dao = dao

    def list_prerequisite_ids_by_blog_id(self, blog_id: str) -> list[uuid.UUID]:
        rows = self.dao.list_by_blog_id(blog_id)
        return [row.prerequisite_id for row in rows]

    def list_prerequisite_ids_by_blog_ids(self, blog_ids: list[str]) -> list:
        """Returns list of BlogPrerequisite rows for the given blog_ids."""
        return self.dao.list_by_blog_ids(blog_ids)

    def create_blog_prerequisite(self, blog_id: str, prerequisite_id: uuid.UUID):
        return self.dao.create(blog_id, prerequisite_id)
