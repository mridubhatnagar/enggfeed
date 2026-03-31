import uuid

from tags.dao import IBlogTagDAO, ITagDAO


class TagService:
    def __init__(self, dao: ITagDAO) -> None:
        self.dao = dao

    def list_tags_by_ids(self, tag_ids: list[uuid.UUID]) -> list:
        return self.dao.list_by_ids(tag_ids)

    def list_all_tags_with_counts(self) -> list:
        return self.dao.list_all_with_counts()

    def get_tag_by_name(self, name: str):
        return self.dao.get_by_name(name)

    def find_similar_tag(self, embedding: list[float], threshold: float) -> tuple:
        return self.dao.find_similar(embedding, threshold)

    def create_tag(self, name: str, embedding: list[float]):
        return self.dao.create(name, embedding)


class BlogTagService:
    def __init__(self, dao: IBlogTagDAO) -> None:
        self.dao = dao

    def list_tag_ids_by_blog_id(self, blog_id: str) -> list[uuid.UUID]:
        rows = self.dao.list_by_blog_id(blog_id)
        return [row.tag_id for row in rows]

    def list_tag_ids_by_blog_ids(self, blog_ids: list[str]) -> list:
        """Returns list of BlogTag rows for the given blog_ids."""
        return self.dao.list_by_blog_ids(blog_ids)

    def list_blog_ids_by_tag_id(self, tag_id: uuid.UUID) -> list[str]:
        rows = self.dao.list_by_tag_id(tag_id)
        return [row.blog_id for row in rows]

    def create_blog_tag(self, blog_id: str, tag_id: uuid.UUID):
        return self.dao.create(blog_id, tag_id)
