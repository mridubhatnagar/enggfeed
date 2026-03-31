---
name: backend-blog
description: Implements the blog/, tags/, and search/ modules — schemas, DAOs, services, handler, and controller.
---

# Backend Blog Sub-agent

## Scope
Create exactly these files:
- `blog/schemas.py`, `blog/dao.py`, `blog/service.py`, `blog/handler.py`, `blog/controller.py`
- `tags/dao.py`, `tags/service.py`
- `search/dao.py`, `search/service.py`

Also add the blog router registration to `app.py` — scoped addition only (see below).

## Context from previous sub-agents
The following files already exist — import from them, do not recreate or modify them:
- `database.py` — `get_db`
- `config.py`
- `constants.py` — `SEARCH_RESULT_LIMIT`, `CONTENT_TIER_LIMITED_MAX_WORDS`, `CONTENT_TIER_PARTIAL_MAX_WORDS`
- `exceptions.py` — `DatabaseError`, `UnauthorizedError`, `NotFoundError`
- `schemas.py` — `APIResponse`, `ErrorDetail`
- `auth/utils.py` — `decode_jwt_token`
- `prerequisites/service.py` — `PrerequisiteService`, `BlogPrerequisiteService`
- ORM models — per-module (`auth/models.py`, `blog/models.py`, `tags/models.py`, etc.)

## Query embedding
`BlogHandler._hybrid_search` embeds the query by calling `embed_text()` from `utils.py` — already implemented by `backend-core`. Import it directly: `from utils import embed_text`.

## Mandatory reads before starting
- `docs/dao_and_service_class_design.md` — exact signatures for `BlogDAO`, `BlogService`, `BlogSourceDAO`, `BlogSourceService`, `BlogChunkDAO`, `BlogChunkService`, `TagDAO`, `TagService`, `BlogTagDAO`, `BlogTagService`, `SearchDAO`, `SearchService`
- `docs/handler_design_guide.md` — `BlogHandler` design, constructor dependencies, `get_blogs`, `get_sources`, `_hybrid_search`, `_reciprocal_rank_fusion`
- `docs/api_contracts.md` — `/api/v1/blogs` and `/api/v1/sources` contracts, `BlogItem`, `PaginatedBlogs`, `BlogSource`, `ContentTier`
- `docs/tech_decisions.md` — search (tsvector, pgvector, RRF formula), search behaviour, return types, error handling

## Hard rules
- Do not add methods to DAO or Service classes beyond `docs/dao_and_service_class_design.md`.
- `search/` has no handler or controller — search is routed entirely through `BlogHandler`.
- `tags/` has no handler or controller — consumed by `BlogHandler` and `IngestHandler` only.
- `SearchDAO` methods use raw SQL via `text()` — do not use ORM for these queries.
- `TagDAO.find_similar` uses pgvector `<=>` cosine distance operator.
- `content_tier` is computed from `word_count` at handler level using thresholds from `constants.py` — never stored in DB.
- Tags and prerequisites populated only for signed-in users (valid JWT present).
- Prerequisites populated only for `PARTIAL` and `FULL` tier — `LIMITED` gets empty array.
- Guest keyword search goes through `BlogService.list_blogs(keyword=...)` — no `SearchService` call.
- `app.py` modification: add the blog router registration only. Do not touch any other part of `app.py`.
- If anything is unclear, stop and ask.

---

## Files

### `blog/schemas.py`
Implement exactly from `docs/api_contracts.md` (`/api/v1/blogs` and `/api/v1/sources` sections):
`ContentTier`, `BlogItem`, `PaginatedBlogs`, `BlogSource`

### `blog/dao.py`
Implement `IBlogDAO`, `BlogDAO`, `IBlogSourceDAO`, `BlogSourceDAO`, `IBlogChunkDAO`, `BlogChunkDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

`BlogDAO.list_blogs`: builds a dynamic SQLAlchemy query — apply only the filters that are not `None`. Keyword search uses tsvector full-text search on the `blog` table. Keyword path excludes `word_count < CONTENT_TIER_LIMITED_MAX_WORDS`.

### `blog/service.py`
Implement `BlogService`, `BlogSourceService`, `BlogChunkService`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `tags/dao.py`
Implement `ITagDAO`, `TagDAO`, `IBlogTagDAO`, `BlogTagDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`.
`TagDAO.find_similar`: pgvector `<=>` cosine distance, returns closest match below threshold or `None`.

### `tags/service.py`
Implement `TagService`, `BlogTagService`.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `search/dao.py`
Implement `ISearchDAO`, `SearchDAO`.
Signatures exactly from `docs/dao_and_service_class_design.md`.
Both methods use raw SQL via `text()`. Details in `docs/tech_decisions.md` (search section) and `docs/dao_and_service_class_design.md` (Search section).

### `search/service.py`
Implement `SearchService`. Thin wrappers only — no business logic.
Signatures exactly from `docs/dao_and_service_class_design.md`.

### `blog/handler.py`
Implement `BlogHandler`. Constructor dependencies and all methods exactly as specified in `docs/handler_design_guide.md`.
Includes private helpers `_hybrid_search` and `_reciprocal_rank_fusion` — specs in `docs/handler_design_guide.md` and RRF formula in `docs/tech_decisions.md`.

### `blog/controller.py`
FastAPI router — routes exactly from `docs/api_contracts.md`:
- `GET /api/v1/blogs` → `APIResponse[PaginatedBlogs]`
- `GET /api/v1/sources` → `APIResponse[list[BlogSource]]`

### `app.py` — scoped addition
Add the blog router import and registration to `app.py` in the router registration section. Do not modify anything else in `app.py`.

---

## Checkpoint — pause here
Stop. Seed `blog_source` and `blog` with test rows via pgadmin before testing.
Notify the user to verify:
- `GET /api/v1/sources` returns list of blog sources
- `GET /api/v1/blogs` returns paginated blogs
- `GET /api/v1/blogs?source=<name>` filters by source correctly
- `GET /api/v1/blogs?page=2&count=5` paginates correctly
- `GET /api/v1/blogs?search=<keyword>` as guest returns keyword-matched results
- `content_tier` computed correctly: `word_count < 150` → `LIMITED`, 150–300 → `PARTIAL`, 300+ → `FULL`
- Signed-in response includes `tags` and `prerequisites` as empty arrays (not missing keys)
- Guest response has empty `tags` and `prerequisites`
