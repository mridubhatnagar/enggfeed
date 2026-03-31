import uuid

from blog.dao import IBlogDAO, IBlogSourceDAO


class BlogSourceService:
    def __init__(self, dao: IBlogSourceDAO) -> None:
        self.dao = dao

    def list_all_sources(self) -> list:
        return self.dao.list_all()

    def get_source_by_id(self, source_id: uuid.UUID):
        return self.dao.get_by_id(source_id)

    def get_source_by_name(self, source: str):
        return self.dao.get_by_source_name(source)

    def get_feed_link_by_source(self, source: str) -> str | None:
        return self.dao.get_feed_link_by_source(source)


class BlogService:
    def __init__(self, dao: IBlogDAO) -> None:
        self.dao = dao

    def get_blog_by_id(self, blog_id: uuid.UUID):
        return self.dao.get_by_id(blog_id)

    def get_blog_by_guid(self, guid: str):
        return self.dao.get_by_guid(guid)

    def get_last_blog_by_source_id(self, source_id: uuid.UUID):
        return self.dao.get_last_by_source_id(source_id)

    def insert_blog(self, blog) -> None:
        self.dao.insert(blog)

    def list_blogs(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
        page: int,
        count: int,
    ) -> list:
        return self.dao.list_blogs(source_ids, tag_ids, keyword, page, count)

    def count_blogs(
        self,
        source_ids: list[uuid.UUID] | None,
        tag_ids: list[uuid.UUID] | None,
        keyword: str | None,
    ) -> int:
        return self.dao.count_blogs(source_ids, tag_ids, keyword)

    def list_blogs_by_ids(self, blog_ids: list[str], page: int, count: int) -> list:
        return self.dao.list_by_ids(blog_ids, page, count)

    def count_blogs_by_ids(self, blog_ids: list[str]) -> int:
        return self.dao.count_by_ids(blog_ids)
