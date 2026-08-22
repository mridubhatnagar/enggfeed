import uuid

from blog.schemas import BlogItem, ContentTier
from blog.service import BlogService, BlogSourceService
from constants import CONTENT_TIER_LIMITED_MAX_WORDS, CONTENT_TIER_PARTIAL_MAX_WORDS
from exceptions import ForbiddenError, NotFoundError
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from simplify.schemas import SimplifyContent, SimplifyDetail
from simplify.service import SimplifyService
from tags.service import BlogTagService, TagService


def _compute_content_tier(word_count: int) -> ContentTier:
    if word_count < CONTENT_TIER_LIMITED_MAX_WORDS:
        return ContentTier.LIMITED
    if word_count < CONTENT_TIER_PARTIAL_MAX_WORDS:
        return ContentTier.PARTIAL
    return ContentTier.FULL


class SimplifyHandler:
    def __init__(
        self,
        blog_service: BlogService,
        blog_source_service: BlogSourceService,
        simplify_service: SimplifyService,
        blog_tag_service: BlogTagService,
        tag_service: TagService,
        blog_prerequisite_service: BlogPrerequisiteService,
        prerequisite_service: PrerequisiteService,
    ) -> None:
        self.blog_service = blog_service
        self.blog_source_service = blog_source_service
        self.simplify_service = simplify_service
        self.blog_tag_service = blog_tag_service
        self.tag_service = tag_service
        self.blog_prerequisite_service = blog_prerequisite_service
        self.prerequisite_service = prerequisite_service

    def get_simplify(self, blog_id: str) -> SimplifyDetail:
        blog = self.blog_service.get_blog_by_id(uuid.UUID(blog_id))
        if blog is None:
            raise NotFoundError(f"Blog not found: {blog_id}")

        tier = _compute_content_tier(blog.word_count)
        if tier in (ContentTier.LIMITED, ContentTier.PARTIAL):
            raise ForbiddenError(
                "Simplify not available for limited or partial tier content"
            )

        simplify_row = self.simplify_service.get_simplify_by_blog_id(blog_id)
        if simplify_row is None:
            raise NotFoundError("Simplify not yet available for this article")

        blog_tag_rows = self.blog_tag_service.list_tag_ids_by_blog_ids(
            [uuid.UUID(blog_id)]
        )
        all_tag_ids = list({row.tag_id for row in blog_tag_rows})
        tag_names: list[str] = []
        if all_tag_ids:
            tag_objects = self.tag_service.list_tags_by_ids(all_tag_ids)
            tag_names = [t.tag for t in tag_objects]

        bp_rows = self.blog_prerequisite_service.list_prerequisite_ids_by_blog_ids(
            [uuid.UUID(blog_id)]
        )
        all_prereq_ids = list({row.prerequisite_id for row in bp_rows})
        prerequisite_names: list[str] = []
        if all_prereq_ids:
            prereq_objects = self.prerequisite_service.list_prerequisites_by_ids(
                all_prereq_ids
            )
            prerequisite_names = [p.topic_name for p in prereq_objects]

        source_obj = self.blog_source_service.get_source_by_id(blog.blog_source_id)
        source_name = source_obj.source if source_obj else ""

        blog_item = BlogItem(
            created_at=blog.created_at,
            link=blog.link,
            title=blog.title,
            thumbnail=blog.thumbnail,
            word_count=blog.word_count,
            published_at=blog.published_at,
            blog_source_id=blog.blog_source_id,
            source=source_name,
            tags=tag_names,
            prerequisites=prerequisite_names,
            content_tier=tier,
        )

        simplify_content = SimplifyContent(
            content=simplify_row.simplify,
            updated_at=simplify_row.updated_at,
        )

        return SimplifyDetail(blog=blog_item, simplify=simplify_content)
