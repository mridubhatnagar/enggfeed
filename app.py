import logging
import secrets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from phoenix.otel import register
from openinference.instrumentation.anthropic import AnthropicInstrumentor

from config import settings

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    environment=settings.ENVIRONMENT,
    integrations=[
        FastApiIntegration(),
        StarletteIntegration(),
        LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
    ],
)

tracer_provider = register(
    project_name="enggsystemfeed",
    endpoint=settings.PHOENIX_ENDPOINT,
)
AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)


app = FastAPI(docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")


_security = HTTPBasic()


def _verify_docs_credentials(credentials: HTTPBasicCredentials = Depends(_security)):
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


from fastapi.openapi.docs import get_swagger_ui_html


@app.get("/docs", include_in_schema=False)
async def swagger_ui(credentials: HTTPBasicCredentials = Depends(_security)):
    _verify_docs_credentials(credentials)
    return get_swagger_ui_html(openapi_url="/openapi.json", title="API Docs")


@app.get("/openapi.json", include_in_schema=False)
async def openapi_spec(credentials: HTTPBasicCredentials = Depends(_security)):
    _verify_docs_credentials(credentials)
    from fastapi.openapi.utils import get_openapi
    return get_openapi(title=app.title, version=app.version, routes=app.routes)


@app.get("/")
def index():
    return FileResponse("templates/index.html")


@app.get("/summary/{blog_id}")
def summary_page(blog_id: str):
    return FileResponse("templates/summary.html")


@app.get("/simplify/{blog_id}")
def simplify_page(blog_id: str):
    return FileResponse("templates/simplify.html")


# [backend-auth] auth router
from auth.controller import router as auth_router
app.include_router(auth_router)

# [backend-blog] blog router
from blog.controller import router as blog_router
app.include_router(blog_router)

# [backend-summary-simplify] summary router
from summary.controller import router as summary_router
app.include_router(summary_router)

# [backend-summary-simplify] simplify router
from simplify.controller import router as simplify_router
app.include_router(simplify_router)

# [backend-prerequisites] prerequisites router
from prerequisites.controller import router as prerequisites_router
app.include_router(prerequisites_router)

# feedback router
from feedback.controller import router as feedback_router
app.include_router(feedback_router)

# ingest router
from ingest.controller import router as ingest_router
app.include_router(ingest_router)

# [backend-ingest] startup ingest
from blog.dao import BlogDAO, BlogSourceDAO
from blog.service import BlogService, BlogSourceService
from database import SessionLocal
from ingest.embedder import Embedder
from ingest.handler import IngestHandler
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from rss_client import RSSClient
from tags.dao import BlogTagDAO, TagDAO
from tags.service import BlogTagService, TagService


def _run_ingest() -> None:
    """Instantiate a fresh DB session and run the ingest pipeline."""
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


def _is_first_run() -> bool:
    from blog.models import Blog
    db = SessionLocal()
    try:
        return db.query(Blog).first() is None
    finally:
        db.close()


if _is_first_run():
    _run_ingest()
