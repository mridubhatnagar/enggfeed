import math
from fastapi import Request

from auth.utils import decode_jwt_token
from blog.schemas import BlogItem, BlogSource, ContentTier, PaginatedBlogs, TagWithCount
from blog.service import BlogService, BlogSourceService
from constants import (
    CONTENT_TIER_LIMITED_MAX_WORDS,
    CONTENT_TIER_PARTIAL_MAX_WORDS,
)
from exceptions import UnauthorizedError
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from schemas import APIResponse, ErrorDetail
from tags.service import BlogTagService, TagService


def _compute_content_tier(word_count: int) -> ContentTier:
    if word_count < CONTENT_TIER_LIMITED_MAX_WORDS:
        return ContentTier.LIMITED
    if word_count < CONTENT_TIER_PARTIAL_MAX_WORDS:
        return ContentTier.PARTIAL
    return ContentTier.FULL


class BlogHandler:
    def __init__(
        self,
        blog_service: BlogService,
        blog_source_service: BlogSourceService,
        blog_tag_service: BlogTagService,
        tag_service: TagService,
        blog_prerequisite_service: BlogPrerequisiteService,
        prerequisite_service: PrerequisiteService,
    ) -> None:
        self.blog_service = blog_service
        self.blog_source_service = blog_source_service
        self.blog_tag_service = blog_tag_service
        self.tag_service = tag_service
        self.blog_prerequisite_service = blog_prerequisite_service
        self.prerequisite_service = prerequisite_service

    def get_blogs(
        self,
        sources: list[str] | None,
        tags: list[str] | None,
        page: int,
        count: int,
        request: Request,
    ) -> APIResponse:
        # Determine if user is signed in — tolerate missing JWT silently
        is_signed_in = False
        try:
            token = request.cookies.get("access_token")
            if token:
                decode_jwt_token(token)
                is_signed_in = True
        except UnauthorizedError:
            is_signed_in = False

        source_ids = None
        tag_ids = None

        if sources:
            resolved = []
            for name in sources:
                row = self.blog_source_service.get_source_by_name(name)
                if row:
                    resolved.append(row.id)
            source_ids = resolved if resolved else None

        if tags:
            resolved = []
            for name in tags:
                row = self.tag_service.get_tag_by_name(name)
                if row:
                    resolved.append(row.tag_id)
            if not resolved:
                # All requested tags unknown — return empty
                paginated = PaginatedBlogs(
                    total=0,
                    page=page,
                    count=count,
                    total_pages=0,
                    blogs={},
                )
                return APIResponse(success=True, data=paginated, error=None)
            tag_ids = resolved

        blogs = self.blog_service.list_blogs(source_ids, tag_ids, None, page, count)
        total = self.blog_service.count_blogs(source_ids, tag_ids, None)

        blog_ids_page = [b.id for b in blogs]
        total_pages = math.ceil(total / count) if count > 0 else 0

        source_ids_page = list({b.blog_source_id for b in blogs})
        source_map: dict = {}
        for sid in source_ids_page:
            src = self.blog_source_service.get_source_by_id(sid)
            if src:
                source_map[sid] = src.source

        tags_by_blog: dict[str, list[str]] = {str(bid): [] for bid in blog_ids_page}
        prerequisites_by_blog: dict[str, list[str]] = {str(bid): [] for bid in blog_ids_page}

        if is_signed_in and blog_ids_page:
            blog_tag_rows = self.blog_tag_service.list_tag_ids_by_blog_ids(blog_ids_page)
            all_tag_ids = list({row.tag_id for row in blog_tag_rows})
            if all_tag_ids:
                tag_objects = self.tag_service.list_tags_by_ids(all_tag_ids)
                tag_id_to_name = {t.tag_id: t.tag for t in tag_objects}
                for row in blog_tag_rows:
                    if str(row.blog_id) in tags_by_blog:
                        tags_by_blog[str(row.blog_id)].append(
                            tag_id_to_name.get(row.tag_id, "")
                        )

            eligible_blog_ids = [
                b.id
                for b in blogs
                if _compute_content_tier(b.word_count) != ContentTier.LIMITED
            ]
            if eligible_blog_ids:
                bp_rows = self.blog_prerequisite_service.list_prerequisite_ids_by_blog_ids(
                    eligible_blog_ids
                )
                all_prereq_ids = list({row.prerequisite_id for row in bp_rows})
                if all_prereq_ids:
                    prereq_objects = self.prerequisite_service.list_prerequisites_by_ids(
                        all_prereq_ids
                    )
                    prereq_id_to_name = {p.id: p.topic_name for p in prereq_objects}
                    for row in bp_rows:
                        if str(row.blog_id) in prerequisites_by_blog:
                            prerequisites_by_blog[str(row.blog_id)].append(
                                prereq_id_to_name.get(row.prerequisite_id, "")
                            )

        blog_items: dict[str, BlogItem] = {}
        for b in blogs:
            tier = _compute_content_tier(b.word_count)
            blog_items[str(b.id)] = BlogItem(
                created_at=b.created_at,
                link=b.link,
                title=b.title,
                thumbnail=b.thumbnail,
                word_count=b.word_count,
                published_at=b.published_at,
                blog_source_id=b.blog_source_id,
                source=source_map.get(b.blog_source_id, ""),
                tags=tags_by_blog.get(str(b.id), []),
                prerequisites=prerequisites_by_blog.get(str(b.id), []),
                content_tier=tier,
            )

        paginated = PaginatedBlogs(
            total=total,
            page=page,
            count=count,
            total_pages=total_pages,
            blogs=blog_items,
        )
        return APIResponse(success=True, data=paginated, error=None)

    def get_sources(self) -> APIResponse:
        sources = self.blog_source_service.list_all_sources()
        result = [BlogSource(id=s.id, source=s.source) for s in sources]
        return APIResponse(success=True, data=result, error=None)

    def get_tags(self) -> APIResponse:
        rows = self.tag_service.list_all_tags_with_counts()
        result = [TagWithCount(tag=tag.tag, count=count) for tag, count in rows]
        return APIResponse(success=True, data=result, error=None)
