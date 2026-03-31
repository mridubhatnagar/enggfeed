import secrets

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from config import settings
from schemas import APIResponse, ErrorDetail

router = APIRouter()


@router.post("/api/v1/ingest", include_in_schema=False)
async def trigger_ingest(x_ingest_secret: str = Header(default="")):
    if not settings.INGEST_SECRET or not secrets.compare_digest(
        x_ingest_secret, settings.INGEST_SECRET
    ):
        return JSONResponse(
            status_code=401,
            content={"success": False, "data": None, "error": {"code": 401, "message": "Unauthorized"}},
        )

    from database import SessionLocal
    from blog.dao import BlogDAO, BlogSourceDAO
    from blog.service import BlogService, BlogSourceService
    from ingest.embedder import Embedder
    from ingest.handler import IngestHandler
    from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
    from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
    from rss_client import RSSClient
    from tags.dao import BlogTagDAO, TagDAO
    from tags.service import BlogTagService, TagService

    db = SessionLocal()
    try:
        handler = IngestHandler(
            blog_source_service=BlogSourceService(BlogSourceDAO(db)),
            blog_service=BlogService(BlogDAO(db)),
            tag_service=TagService(TagDAO(db)),
            blog_tag_service=BlogTagService(BlogTagDAO(db)),
            prerequisite_service=PrerequisiteService(PrerequisiteDAO(db)),
            blog_prerequisite_service=BlogPrerequisiteService(BlogPrerequisiteDAO(db)),
            rss_client=RSSClient(),
            embedder=Embedder(),
        )
        handler.trigger_job()
    finally:
        db.close()

    return APIResponse(success=True, data={"message": "Ingest complete"}, error=None)
