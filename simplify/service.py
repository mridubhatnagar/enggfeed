from simplify.dao import ISimplifyDAO


class SimplifyService:
    def __init__(self, dao: ISimplifyDAO) -> None:
        self.dao = dao

    def get_simplify_by_blog_id(self, blog_id: str, use_cache: bool = True, force_update: bool = False):
        return self.dao.get_by_blog_id(blog_id, use_cache=use_cache, force_update=force_update)

    def create_simplify(self, blog_id: str, simplify: str):
        return self.dao.create(blog_id, simplify)

    def update_simplify(self, blog_id: str, simplify: str):
        return self.dao.update(blog_id, simplify)
