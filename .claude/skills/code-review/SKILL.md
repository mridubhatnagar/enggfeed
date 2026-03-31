---
name: code-review
description: Review code against all architecture, layer, caching, error handling, and frontend rules for the enggsystemfeed project.
---

Review the code in $ARGUMENTS against all project rules below. Report every violation clearly — file path, line number, rule broken, and what the fix should be. If no violations are found, say so explicitly.

---

## 1. Layered Architecture

`Controller → Handler → Service → DAO` — strictly in this direction. Flag any bypass.

- Controllers must never import or call DAO classes directly.
- Handlers must never import DAO classes directly — all data access through services.
- Services must never call other services — cross-service coordination belongs in the handler of the module initiating the action.
- DAOs must contain no business logic — only database queries.

## 2. Dependency Injection

- DAOs injected into services via `__init__`. Services injected into handlers via `__init__`. Handlers injected into controllers via FastAPI `Depends`.
- No class instantiates its own dependencies internally.

## 3. Return Types

- DAO methods return SQLAlchemy ORM model instances or `list[Model]`. Return `None` when not found.
- Service methods pass ORM models through unchanged — same return types as DAO.
- Handler methods convert ORM models to Pydantic schemas and return `APIResponse[T]`. Conversion only happens in handlers, never in DAOs or services.

## 4. Caching

- `@cache.cached` decorator belongs on DAO methods only.
- DAO methods must accept `use_cache: bool = True`.
- Only handlers may decide to pass `use_cache=False` — and only after a staleness check (`check_refresh_due()`). Controllers must never pass it.
- Flow: handler passes `use_cache` to service → service passes it to DAO.

## 5. Error Handling

- DAO layer: catches SQLAlchemy exceptions, re-raises as `DatabaseError`.
- Handler layer: raises `NotFoundError`, `ForbiddenError`, `AuthError`, `UnauthorizedError`, `RSSFeedError`, `LLMUnreachableError`, or `SearchUnreachableError`. Lets `DatabaseError` propagate.
- Controller layer: catches all exceptions, converts to `APIResponse(success=False, error=ErrorDetail(...))` with correct HTTP status:
  - `DatabaseError` → 500
  - `UnauthorizedError` / `AuthError` → 401
  - `ForbiddenError` → 403
  - `NotFoundError` → 404
  - `RSSFeedError` / `LLMUnreachableError` → 502
- Embedding failures must raise `SearchUnreachableError` — not `LLMUnreachableError`.
- All responses use `APIResponse[T]` envelope (`success`, `data`, `error` fields always present).

## 6. Shared Utilities

- `call_llm()`, `embed_text()`, and `check_refresh_due()` live in `utils.py` at project root — not inlined in handlers.
- `embed_text()` raises `SearchUnreachableError` on failure.
- `call_llm()` raises `LLMUnreachableError` on failure.
- Auth-specific utilities (`generate_jwt_token`, `decode_jwt_token`) live in `auth/utils.py` only.
- Google OAuth HTTP calls live in `auth/client.py` (`AuthClient` class) only.

## 7. Prompts

- All prompt templates live in `prompts/` — `summary.py`, `simplify.py`, `prerequisites.py`, `ingest.py`.
- Handlers import prompts directly: `from prompts.summary import SUMMARY_PROMPT`. Never defined inline in handlers or elsewhere.

## 8. ORM Models

- Models are per-module: `auth/models.py`, `blog/models.py`, `tags/models.py`, `prerequisites/models.py`, `summary/models.py`, `simplify/models.py`.
- `Base` is always imported from `database.py`.
- Model files are read-only — no other module may modify them.

## 9. Schemas

- Each module owns its Pydantic schemas in `module/schemas.py` — no shared inheritance across modules.
- `APIResponse[T]` and `ErrorDetail` live in `schemas.py` at project root — do not redefine them elsewhere.
- `ContentTier` enum lives in `blog/schemas.py` only.
- `content_tier` is computed from `word_count` at handler level using thresholds from `constants.py` — never stored in DB.

## 10. Search

- `search/` has no handler or controller — search is routed entirely through `BlogHandler`.
- `tags/` has no handler or controller.
- Guest keyword search: goes through `BlogService.list_blogs(keyword=...)` — `SearchService` is never involved for guests.
- Signed-in hybrid search: `BlogHandler._hybrid_search` calls `embed_text()`, then `SearchService.keyword_search` + `SearchService.vector_search`, then `_reciprocal_rank_fusion`.
- `SearchDAO` methods use raw SQL via `text()` — do not use ORM for these queries.

## 11. `app.py`

Each sub-agent has a scoped section — no code may be written outside its section:
- `backend-core`: app instance, `GET /` route, `/docs` Basic Auth, `static/` mount
- `backend-auth`: auth router registration only
- `backend-blog`: blog router registration only
- `backend-summary-simplify`: summary + simplify router registrations only
- `backend-prerequisites`: prerequisites router registration only
- `backend-ingest`: APScheduler wiring only

## 12. Frontend

- Alpine.js only — no other JS framework or library.
- No full page reloads on filter, search, paginate, or tag click — Alpine.js updates the DOM in place.
- URL updated via `history.pushState` on filter, paginate, tag click, and search.
- Every API call must match `docs/api_contracts.md` exactly — endpoint paths, query param names, response field names.
- `GET /` returns `FileResponse("templates/index.html")` — no Jinja2, no server-side rendering.
- CSS, JS, images served from `static/` mounted at `/static`.
- Brand/accent color is `#4F46E5` — used consistently.
- No hardcoded blog data — all content loaded via AJAX.

## 13. Module Boundaries

- Each module contains logic for its own responsibility only.
- Cross-module coordination belongs in the handler of the module initiating the action.
- Do not add methods to DAO or Service classes not defined in `docs/dao_and_service_class_design.md`.
- Do not create new files outside the folder structure in `CLAUDE.md`.
- Do not install new dependencies without explicit instruction.

## 14. Ingest-specific Rules

- Limited tier articles (`word_count < CONTENT_TIER_LIMITED_MAX_WORDS`) are skipped — never reach chunker or embedder.
- `_fetch_thumbnail` must never raise — any failure returns `None` silently.
- LLM failure on a single article → log error, skip that article, continue.
- RSS feed failure for a source → log error, skip that source, continue.
- Tag normalisation: lowercase → strip whitespace → collapse hyphens/underscores/spaces to `-` → embed → cosine similarity check (threshold 0.95).
- `blog.id` is the RSS `guid` (Text PK) — duplicate inserts prevented by PK constraint, no separate dedup logic needed.
- Summary and simplify tables are never populated at ingest — only on first user request.
