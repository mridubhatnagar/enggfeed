from summary.dao import ISummaryDAO


class SummaryService:
    def __init__(self, dao: ISummaryDAO) -> None:
        self.dao = dao

    def get_summary_by_blog_id(self, blog_id: str, use_cache: bool = True, force_update: bool = False):
        return self.dao.get_by_blog_id(blog_id, use_cache=use_cache, force_update=force_update)

    def create_summary(self, blog_id: str, content: dict):
        return self.dao.create(blog_id, content)

    def update_summary(self, blog_id: str, content: dict):
        return self.dao.update(blog_id, content)
