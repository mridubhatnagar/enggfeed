import secrets

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from blog.dao import BlogDAO, BlogSourceDAO
from blog.service import BlogService, BlogSourceService
from config import settings
from database import SessionLocal
from ingest.dao import LLMUsageDAO
from ingest.embedder import Embedder
from ingest.handler import IngestHandler
from ingest.service import LLMUsageService
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from rss_client import RSSClient
from schemas import APIResponse, ErrorDetail
from simplify.dao import SimplifyDAO
from simplify.service import SimplifyService
from summary.dao import SummaryDAO
from summary.service import SummaryService
from tags.dao import BlogTagDAO, TagDAO
from tags.service import BlogTagService, TagService

router = APIRouter()


@router.post("/api/v1/ingest", include_in_schema=False)
def trigger_ingest(x_ingest_secret: str = Header(default="")):
    if not settings.INGEST_SECRET or not secrets.compare_digest(
        x_ingest_secret, settings.INGEST_SECRET
    ):
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "data": None,
                "error": {"code": 401, "message": "Unauthorized"},
            },
        )

    db = SessionLocal()
    try:
        handler = IngestHandler(
            blog_source_service=BlogSourceService(BlogSourceDAO(db)),
            blog_service=BlogService(BlogDAO(db)),
            tag_service=TagService(TagDAO(db)),
            blog_tag_service=BlogTagService(BlogTagDAO(db)),
            prerequisite_service=PrerequisiteService(PrerequisiteDAO(db)),
            blog_prerequisite_service=BlogPrerequisiteService(BlogPrerequisiteDAO(db)),
            summary_service=SummaryService(SummaryDAO(db)),
            simplify_service=SimplifyService(SimplifyDAO(db)),
            rss_client=RSSClient(),
            embedder=Embedder(),
            llm_usage_service=LLMUsageService(LLMUsageDAO(db)),
        )
        handler.trigger_job()
    finally:
        db.close()

    return APIResponse(success=True, data={"message": "Ingest complete"}, error=None)
