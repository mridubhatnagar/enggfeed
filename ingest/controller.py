import logging
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import sentry_sdk
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    status,
)
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

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

_security = HTTPBasic()


def _verify_cost_credentials(credentials: HTTPBasicCredentials = Depends(_security)):
    """Same admin credentials as /docs — this endpoint exposes internal
    LLM spend, not a user-facing feature."""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.SWAGGER_USERNAME.encode("utf-8"),
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        settings.SWAGGER_PASSWORD.encode("utf-8"),
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


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


def _months_ago(dt: datetime, months: int) -> datetime:
    """Calendar-month subtraction (not a 30-day approximation)."""
    total_months = dt.year * 12 + (dt.month - 1) - months
    year, month = divmod(total_months, 12)
    return dt.replace(
        year=year, month=month + 1, day=1, hour=0, minute=0, second=0, microsecond=0
    )


@router.get("/api/v1/cost", include_in_schema=False)
def get_cost(
    days: int = Query(default=30, ge=1, le=365),
    months: int = Query(default=12, ge=1, le=60),
    _: None = Depends(_verify_cost_credentials),
):
    db = SessionLocal()
    try:
        service = LLMUsageService(LLMUsageDAO(db))
        now = datetime.now(timezone.utc)

        daily_since = now - timedelta(days=days)
        daily_rows = service.get_daily_costs(daily_since)
        daily = [
            {
                "day": row.day.date().isoformat(),
                "calls": row.calls,
                "cost_usd": str(row.cost_usd),
            }
            for row in daily_rows
        ]

        monthly_since = _months_ago(now, months)
        monthly_rows = service.get_monthly_costs(monthly_since)
        monthly = [
            {
                "month": row.month.date().isoformat()[:7],  # "YYYY-MM"
                "calls": row.calls,
                "cost_usd": str(row.cost_usd),
            }
            for row in monthly_rows
        ]

        return APIResponse(
            success=True,
            data={
                "daily_since": daily_since.date().isoformat(),
                "total_calls_daily_window": sum(row.calls for row in daily_rows),
                "total_cost_usd_daily_window": str(
                    sum((row.cost_usd for row in daily_rows), Decimal("0"))
                ),
                "daily": daily,
                "monthly_since": monthly_since.date().isoformat()[:7],
                "total_calls_monthly_window": sum(row.calls for row in monthly_rows),
                "total_cost_usd_monthly_window": str(
                    sum((row.cost_usd for row in monthly_rows), Decimal("0"))
                ),
                "monthly": monthly,
            },
            error=None,
        )
    finally:
        db.close()
