---
name: backend-core
description: Implements core project files — config.py, constants.py, exceptions.py, schemas.py, database.py, utils.py, rss_client.py, app.py, and all __init__.py files.
---

# Backend Core Sub-agent

## Scope
Create exactly these files:
- `config.py`, `constants.py`, `exceptions.py`, `schemas.py`, `database.py`, `utils.py`, `rss_client.py`, `app.py`
- `__init__.py` in every module directory: `auth/`, `blog/`, `tags/`, `summary/`, `simplify/`, `prerequisites/`, `search/`, `ingest/`, `prompts/`

Do not create any other files. Do not implement any module logic.

## Mandatory reads before starting
- `CLAUDE.md` — folder structure, module responsibilities, architecture rules
- `docs/tech_decisions.md` — config, caching, auth, error handling, LLM, APScheduler, Swagger protection
- `docs/api_contracts.md` — base `APIResponse` schema, `GET /` route

## Hard rules
- Do not implement any module-level logic (no DAOs, services, handlers, controllers).
- `app.py` must be created with explicit placeholder comments — subsequent sub-agents will add to it. Do not import module routers or `IngestHandler` here.
- All `__init__.py` files are empty.
- If anything is unclear, stop and ask.

---

## Files

### `config.py`
Use Pydantic `BaseSettings`. Load from environment:
- `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `JWT_ALGORITHM` (default `"HS256"`), `JWT_EXPIRY_HOURS` (default `2`), `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `LLM_TIMEOUT_SECONDS` (default `30`), `SWAGGER_USERNAME`, `SWAGGER_PASSWORD`, `PHOENIX_ENDPOINT` (default `"http://phoenix:4318/v1/traces"`)

### `constants.py`
Exactly these four constants, nothing more:
- `SEARCH_RESULT_LIMIT = 30`
- `CONTENT_TIER_LIMITED_MAX_WORDS = 150`
- `CONTENT_TIER_PARTIAL_MAX_WORDS = 300`
- `REFRESH_INTERVAL_DAYS = 7`

### `exceptions.py`
Exactly these exception classes, all extending `Exception`, nothing more:
`DatabaseError`, `UnauthorizedError`, `AuthError`, `ForbiddenError`, `NotFoundError`, `RSSFeedError`, `LLMUnreachableError`, `SearchUnreachableError`

### `schemas.py`
Base response envelope used by all modules:
```python
T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: int
    message: str

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None
```

### `database.py`
- SQLAlchemy engine from `DATABASE_URL` in `config.py`
- `SessionLocal` using that engine
- `Base = declarative_base()`
- `get_db()` generator for FastAPI `Depends` — yields a session, closes on exit

### `utils.py`
Three functions only — specs in `docs/tech_decisions.md`:
- `check_refresh_due(updated_at: datetime | None) -> bool` — `True` if `None` or older than `REFRESH_INTERVAL_DAYS`
- `call_llm(prompt: str, timeout: int | None = None) -> str` — calls LLM, uses `response_format: json_object`, raises `LLMUnreachableError` on timeout or failure
- `embed_text(text: str) -> list[float]` — calls OpenAI `text-embedding-3-small`, returns embedding vector, raises `SearchUnreachableError` on failure

### `rss_client.py`
`RSSClient` class — two methods only, specs in `docs/tech_decisions.md` (RSSClient section):
- `get_feed(feed_url: str) -> list[dict]`
- `get_content(feed_url: str, guid: str) -> str`

### `app.py`
Create the FastAPI app skeleton with explicit placeholders. No module imports yet.

Initialize Phoenix tracer at module level, before the router registration placeholders:

```python
from phoenix.otel import register
from openinference.instrumentation.anthropic import AnthropicInstrumentor

tracer_provider = register(
    project_name="enggsystemfeed",
    endpoint=settings.PHOENIX_ENDPOINT,
)
AnthropicInstrumentor().instrument(tracer_provider=tracer_provider)

# --- Router registrations ---
# Each backend sub-agent will add its router here.
# auth router — added by backend-auth
# blog router — added by backend-blog
# summary router — added by backend-summary-simplify
# simplify router — added by backend-summary-simplify
# prerequisites router — added by backend-prerequisites

# --- APScheduler ---
# Wired by backend-ingest after IngestHandler exists.
```

Implement:
- Mount `static/` directory as `StaticFiles` at `/static`
- `GET /` — returns `FileResponse("templates/index.html")`. This is a stub — the frontend agent will replace `templates/index.html` with the real HTML shell.
- `/docs` protection with HTTP Basic Auth using `SWAGGER_USERNAME`/`SWAGGER_PASSWORD` from `config.py` — return 401 if credentials are missing or wrong

Also create:
- `templates/index.html` — stub file: `<html><body>Loading...</body></html>`
- `static/` — empty directory (add a `.gitkeep`)

### `__init__.py`
Create empty `__init__.py` in: `auth/`, `blog/`, `tags/`, `summary/`, `simplify/`, `prerequisites/`, `search/`, `ingest/`, `prompts/`

---

## Checkpoint — pause here
Stop. Do not proceed. Notify the user to verify:
- App starts without import errors (`docker compose logs app`)
- `http://localhost:8000/docs` returns 401 without credentials, 200 with correct credentials
- `GET /` returns an HTML response
