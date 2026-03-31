from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from blog.dao import BlogDAO, BlogSourceDAO
from blog.handler import BlogHandler
from blog.service import BlogService, BlogSourceService
from database import get_db
from exceptions import DatabaseError
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from schemas import APIResponse, ErrorDetail
from tags.dao import BlogTagDAO, TagDAO
from tags.service import BlogTagService, TagService

router = APIRouter()


def get_blog_handler(db: Session = Depends(get_db)) -> BlogHandler:
    blog_dao = BlogDAO(db)
    blog_source_dao = BlogSourceDAO(db)
    tag_dao = TagDAO(db)
    blog_tag_dao = BlogTagDAO(db)
    prerequisite_dao = PrerequisiteDAO(db)
    blog_prerequisite_dao = BlogPrerequisiteDAO(db)

    return BlogHandler(
        blog_service=BlogService(blog_dao),
        blog_source_service=BlogSourceService(blog_source_dao),
        blog_tag_service=BlogTagService(blog_tag_dao),
        tag_service=TagService(tag_dao),
        blog_prerequisite_service=BlogPrerequisiteService(blog_prerequisite_dao),
        prerequisite_service=PrerequisiteService(prerequisite_dao),
    )


@router.get("/api/v1/blogs")
async def get_blogs(
    request: Request,
    source: str | None = None,
    tag: str | None = None,
    page: int = 1,
    count: int = 20,
    handler: BlogHandler = Depends(get_blog_handler),
):
    sources = [s.strip() for s in source.split(",") if s.strip()] if source else None
    tags = [t.strip() for t in tag.split(",") if t.strip()] if tag else None
    try:
        return handler.get_blogs(
            sources=sources,
            tags=tags,
            page=page,
            count=count,
            request=request,
        )
    except DatabaseError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
    except Exception as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )


@router.get("/api/v1/sources")
async def get_sources(handler: BlogHandler = Depends(get_blog_handler)):
    try:
        return handler.get_sources()
    except DatabaseError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
    except Exception as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )


@router.get("/api/v1/tags")
async def get_tags(handler: BlogHandler = Depends(get_blog_handler)):
    try:
        return handler.get_tags()
    except DatabaseError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
    except Exception as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=500, message=str(exc)),
        )
