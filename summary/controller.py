from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from blog.dao import BlogDAO, BlogSourceDAO
from blog.service import BlogService, BlogSourceService
from database import get_db
from exceptions import DatabaseError, ForbiddenError, NotFoundError
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from schemas import APIResponse, ErrorDetail
from summary.dao import SummaryDAO
from summary.handler import SummaryHandler
from summary.service import SummaryService
from tags.dao import BlogTagDAO, TagDAO
from tags.service import BlogTagService, TagService

router = APIRouter()


def get_summary_handler(db: Session = Depends(get_db)) -> SummaryHandler:
    blog_dao = BlogDAO(db)
    blog_source_dao = BlogSourceDAO(db)
    summary_dao = SummaryDAO(db)
    tag_dao = TagDAO(db)
    blog_tag_dao = BlogTagDAO(db)
    prerequisite_dao = PrerequisiteDAO(db)
    blog_prerequisite_dao = BlogPrerequisiteDAO(db)

    return SummaryHandler(
        blog_service=BlogService(blog_dao),
        blog_source_service=BlogSourceService(blog_source_dao),
        summary_service=SummaryService(summary_dao),
        blog_tag_service=BlogTagService(blog_tag_dao),
        tag_service=TagService(tag_dao),
        blog_prerequisite_service=BlogPrerequisiteService(blog_prerequisite_dao),
        prerequisite_service=PrerequisiteService(prerequisite_dao),
    )


@router.get("/api/v1/blogs/{blog_id}/summary")
def get_summary(
    blog_id: str,
    handler: SummaryHandler = Depends(get_summary_handler),
):
    try:
        result = handler.get_summary(blog_id=blog_id)
        return APIResponse(success=True, data=result, error=None)
    except ForbiddenError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=403, message=str(exc)),
        )
    except NotFoundError as exc:
        return APIResponse(
            success=False,
            data=None,
            error=ErrorDetail(code=404, message=str(exc)),
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
