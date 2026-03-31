---
name: backend-summary-simplify
description: Implements the summary/ and simplify/ modules — schemas, DAOs, services, handlers, and controllers.
---

# Backend Summary + Simplify Sub-agent

## Scope
Create exactly these files:
- `summary/schemas.py`, `summary/dao.py`, `summary/service.py`, `summary/handler.py`, `summary/controller.py`
- `simplify/schemas.py`, `simplify/dao.py`, `simplify/service.py`, `simplify/handler.py`, `simplify/controller.py`

Also add summary and simplify router registrations to `app.py` — scoped addition only (see below).

## Context from previous sub-agents
The following files already exist — import from them, do not recreate or modify them:
- `database.py` — `get_db`
- `config.py`
- `constants.py` — `CONTENT_TIER_LIMITED_MAX_WORDS`, `CONTENT_TIER_PARTIAL_MAX_WORDS`, `REFRESH_INTERVAL_DAYS`
- `exceptions.py` — `DatabaseError`, `UnauthorizedError`, `ForbiddenError`, `NotFoundError`, `RSSFeedError`, `LLMUnreachableError`
- `schemas.py` — `APIResponse`, `ErrorDetail`
- `utils.py` — `check_refresh_due`, `call_llm`
- `rss_client.py` — `RSSClient`
- `auth/utils.py` — `decode_jwt_token`
- `blog/schemas.py` — `BlogItem`, `ContentTier`
- `blog/service.py` — `BlogService`, `BlogSourceService`
- `tags/service.py` — `TagService`, `BlogTagService`
- `prerequisites/service.py` — `PrerequisiteService`, `BlogPrerequisiteService`
- ORM models — location confirmed by orchestrator
- `prompts/summary.py` and `prompts/simplify.py` — exist as stubs (`SUMMARY_PROMPT = None`, `SIMPLIFY_PROMPT = None`)

## Mandatory reads before starting
- `docs/dao_and_service_class_design.md` — exact signatures for `SummaryDAO`, `SummaryService`, `SimplifyDAO`, `SimplifyService`
- `docs/handler_design_guide.md` — `SummaryHandler` and `SimplifyHandler` designs, constructor dependencies, cache → DB → LLM flow, 7-day refresh logic, content tier gating, invariants
- `docs/api_contracts.md` — `/api/v1/blogs/{blog_id}/summary` and `/api/v1/blogs/{blog_id}/simplify` contracts
- `docs/tech_decisions.md` — caching strategy (Cache Aside), `use_cache` rules, error handling and status code mapping

## Hard rules
- Do not add methods to DAO or Service classes beyond `docs/dao_and_service_class_design.md`.
- **Invariant — summary:** A `summary` row is never created at ingest time. Do not add any code path that assumes a summary row exists for an ingested blog.
- **Invariant — simplify:** A `simplify` row is never created at ingest time. Same rule applies.
- `SummaryHandler`: returns `403` for `LIMITED` tier. `SimplifyHandler`: returns `403` for `LIMITED` and `PARTIAL` tiers.
- Only handlers pass `use_cache=False` — never controllers.
- `app.py` modification: add summary and simplify router registrations only. Do not touch any other part of `app.py`.
- Prerequisites enrichment on summary/simplify pages: `blog_prerequisite_service` and `prerequisite_service` are constructor dependencies of both handlers per `docs/handler_design_guide.md` — inject them. Both services already exist from `backend-prerequisites`.
- If anything is unclear, stop and ask.

---

## Files

### `summary/schemas.py`
Implement exactly from `docs/api_contracts.md` (summary endpoint section):
`SummaryContent`, `SummaryDetail`

### `summary/dao.py`
Implement `ISummaryDAO`, `SummaryDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `summary/service.py`
Implement `SummaryService`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `summary/handler.py`
Implement `SummaryHandler`. Constructor dependencies and `get_summary` exactly as specified in `docs/handler_design_guide.md`.
Prompt imported from `prompts/summary.py`.

### `summary/controller.py`
FastAPI router. Route: `GET /api/v1/blogs/{blog_id}/summary` → `APIResponse[SummaryDetail]`

### `simplify/schemas.py`
Implement exactly from `docs/api_contracts.md` (simplify endpoint section):
`SimplifyContent`, `SimplifyDetail`

### `simplify/dao.py`
Implement `ISimplifyDAO`, `SimplifyDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `simplify/service.py`
Implement `SimplifyService`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `simplify/handler.py`
Implement `SimplifyHandler`. Constructor dependencies and `get_simplify` exactly as specified in `docs/handler_design_guide.md`.
Prompt imported from `prompts/simplify.py`.

### `simplify/controller.py`
FastAPI router. Route: `GET /api/v1/blogs/{blog_id}/simplify` → `APIResponse[SimplifyDetail]`

### `app.py` — scoped addition
Add summary and simplify router imports and registrations to `app.py` in the router registration section. Do not modify anything else in `app.py`.

---

## Checkpoint — pause here
Stop. Use a blog row with a valid `guid` and `blog_source_id` pointing to a real RSS feed.
Notify the user to verify:
- `GET /api/v1/blogs/{blog_id}/summary` as signed-in returns summary on first call (LLM invoked)
- Second call returns same result instantly — no second LLM call in logs (served from cache)
- `summary` row exists in DB with `updated_at` set
- Cache entry visible in RedisInsight
- Guest request → 401
- `LIMITED` tier blog → 403
- `GET /api/v1/blogs/{blog_id}/simplify` for `FULL` tier → returns ELI5 content
- `PARTIAL` tier → 403
- `LIMITED` tier → 403
