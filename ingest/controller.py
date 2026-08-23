import logging
import secrets

import sentry_sdk
from fastapi import APIRouter, BackgroundTasks, Header
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

logger = logging.getLogger(__name__)

router = APIRouter()


def _run_ingest_job() -> None:
    """Build dependencies and run the ingest pipeline. Runs as a background task,
    after the HTTP response has already been sent — errors have no request to
    propagate to, so they're captured to Sentry and logged instead."""
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
    except Exception as exc:
        sentry_sdk.capture_exception(exc)
        logger.error("Ingest job failed: %s", exc, exc_info=True)
    finally:
        db.close()


@router.post("/api/v1/ingest", include_in_schema=False)
def trigger_ingest(
    background_tasks: BackgroundTasks, x_ingest_secret: str = Header(default="")
):
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

    background_tasks.add_task(_run_ingest_job)
    return APIResponse(success=True, data={"message": "Ingest started"}, error=None)
