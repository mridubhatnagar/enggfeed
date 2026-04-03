# CLAUDE.md

## Project Brief

A one-stop aggregator for engineering blogs from big tech companies. Users can browse and filter by company. Signed-in users additionally get browsable topic tags, prerequisite topics, on-demand summaries, and simplified (ELI5) explanations.

**Stack:** FastAPI (backend) + Alpine.js (frontend) + PostgreSQL + Redis

**Key design decisions:**
- Content is not stored — fetched on demand for LLM calls, raw content discarded after.
- Summary and simplify are regenerated every 7 days — DB and cache both updated. Tags are stable once set.
- RSS feeds polled once per day via GitHub Actions. Articles inserted oldest-first; last DB record per feed is always the most recent article.
- pgvector used for tag and prerequisite normalization at ingest (cosine similarity) — not for search.

## Design Docs

| File | What's in it |
|------|-------------|
| `docs/product_decisions.md` | Product features, user tiers, content tiers, ads, UX behavior |
| `docs/tech_decisions.md` | Tech stack, folder structure, auth flow, caching strategy, ingest pipeline, search |
| `docs/ux_decisions.md` | UI layout, card behavior, page designs, empty states, pagination UX |
| `docs/schema.md` | DB schema, table reasoning, ER diagram |
| `docs/dao_and_service_class_design.md` | DAO and Service class signatures |
| `docs/handler_design_guide.md` | Handler class designs — business logic flow per module |
| `docs/api_contracts.md` | API endpoint contracts |
| `docs/pending_decisions.md` | Open decisions not yet resolved — check before implementing the relevant module |
| `docs/v2_features.md` | Features deferred from v1 — evals, prompt versioning, prerequisite content depth |

---

## Folder Structure

```
enggsystemfeed/
├── app.py
├── config.py
├── constants.py
├── database.py
├── exceptions.py
├── schemas.py
├── utils.py
├── rss_client.py
├── Dockerfile
├── docker-compose.yml
├── auth/
│   ├── __init__.py
│   ├── client.py
│   ├── controller.py
│   ├── dao.py
│   ├── schemas.py
│   ├── service.py
│   ├── handler.py
│   └── utils.py
├── blog/
│   ├── __init__.py
│   ├── controller.py
│   ├── dao.py
│   ├── schemas.py
│   ├── service.py
│   └── handler.py
├── tags/
│   ├── __init__.py
│   ├── dao.py
│   └── service.py
├── summary/
│   ├── __init__.py
│   ├── controller.py
│   ├── dao.py
│   ├── schemas.py
│   ├── service.py
│   └── handler.py
├── simplify/
│   ├── __init__.py
│   ├── controller.py
│   ├── dao.py
│   ├── schemas.py
│   ├── service.py
│   └── handler.py
├── prerequisites/
│   ├── __init__.py
│   ├── controller.py
│   ├── dao.py
│   ├── schemas.py
│   ├── service.py
│   └── handler.py
├── ingest/
│   ├── __init__.py
│   ├── controller.py
│   ├── handler.py
│   └── embedder.py
├── prompts/
│   ├── __init__.py
│   ├── summary.py
│   ├── simplify.py
│   ├── prerequisites.py
│   └── ingest.py
├── feedback/
│   ├── __init__.py
│   ├── controller.py
│   ├── dao.py
│   ├── enums.py
│   ├── schemas.py
│   ├── service.py
│   └── handler.py
```

## Module Responsibilities

| Module | Responsible for |
|--------|----------------|
| `auth/` | Google OAuth flow, state token verification, allowlist check, JWT issuance and validation |
| `blog/` | Blog listing, filtering by source and tag, pagination. Also owns `BlogSource` DAO and Service |
| `summary/` | On-demand summary generation, 7-day refresh logic, cache management via `@cache.cached` |
| `simplify/` | ELI5 generation, 7-day refresh logic, cache management |
| `tags/` | Tag lookup by name, tag filtering on feed. Owns `Tag` and `BlogTag` DAO and Service |
| `prerequisites/` | On-demand prerequisite explanation generation, 7-day refresh logic, cache management. Owns `Prerequisite` and `BlogPrerequisite` DAO and Service |
| `ingest/` | RSS polling, og:image scraping, embedding, storing articles, tagging pipeline, prerequisites extraction. Exposes `POST /api/v1/ingest` endpoint triggered by GitHub Actions daily cron |
| `feedback/` | User feedback submission for tags, prerequisites, summary, and simplify. Rate limiting via Redis. Exposes `POST /api/v1/feedback` endpoint |
| `prompts/` | All LLM prompt templates — `summary.py`, `simplify.py`, `prerequisites.py`, `ingest.py` |

**Rules:**
- Each module must only contain logic for its own responsibility.
- Cross-module coordination belongs in the handler of the module initiating the action.
- Do not add methods to DAO or Service classes not defined in `docs/dao_and_service_class_design.md`.
- Do not create new files outside the folder structure defined in this file.
- Do not install new dependencies without explicit instruction.

---

## Architecture

The codebase follows a strict layered architecture:

```
Controller → Handler → Service → DAO
```

- **Controller** — HTTP layer. Parses requests, calls handler, returns responses.
- **Handler** — Business logic layer. Orchestrates services, applies rules. Implemented as a class with services injected via constructor.
- **Service** — Thin layer over DAO. One service per DAO.
- **DAO** — Database access only. No business logic.

## Rules

### Layer access rules
- Controllers must never import or call DAO classes directly. All data access goes through the service layer.
- Handlers must not import DAO classes directly. Handlers call services.
- Services must not call other services. Cross-service coordination belongs in the handler.
- DAOs must contain no business logic — only database queries.

### Dependency Injection
- Dependencies are injected via constructors — DAOs into services, services into handlers, handlers into controllers.
- No class instantiates its own dependencies internally.
- FastAPI's `Depends` is used for injecting dependencies into controllers.

### Caching
- DAO methods use `@cache.cached` decorator for transparent cache handling.
- DAO methods accept `use_cache: bool = True` — pass `False` to bypass cache and hit DB directly.
- Only handlers decide when to pass `use_cache=False`. Controllers must never pass it.

### Prompts
- All prompts live in the shared `prompts/` module — `summary.py`, `simplify.py`, `prerequisites.py`, `ingest.py`.
- Handlers import prompts directly from `prompts/` — e.g., `from prompts.summary import SUMMARY_PROMPT`.

### LLM and shared utilities
- `utils.py` at project root contains shared utilities: `check_refresh_due()`, `call_llm()`.
- `auth/utils.py` contains auth-specific utilities: `generate_jwt_token()`, `decode_jwt_token()`.
- `auth/client.py` contains `AuthClient` — wraps Google OAuth HTTP calls.

### HTML comments
- Do not use banner-style section divider comments (e.g. `<!-- ═══ SECTION ═══ -->`). Use plain inline comments only where the logic is not self-evident.
