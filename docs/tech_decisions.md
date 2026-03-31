# Tech Design: Engineering Blog Aggregator

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
├── search/
│   ├── __init__.py
│   ├── service.py
│   └── dao.py
├── ingest/
│   ├── __init__.py
│   ├── handler.py           # orchestrates fetch → chunk → embed → store
│   ├── chunker.py
│   └── embedder.py
├── prompts/
│   ├── __init__.py
│   ├── summary.py
│   ├── simplify.py
│   ├── prerequisites.py
│   └── ingest.py
```

**Note:** `search` module uses `dao.py` + `service.py` only — no handler or controller. Search is routed through `BlogHandler`.

---

## RSS Ingest
- Poll each feed once per day
- RSS feeds return items latest first
- Articles are inserted oldest first — last record in DB for a feed is always the most recent article
- RSS content is used as-is — no scraping of the full article URL. Whatever the feed provides is what gets stored and embedded. Content tiers handle variation in RSS content length — do not add scraping as a fallback.

**Flow 1 — Initial ingest (empty DB):**
1. Fetch RSS feed (latest first)
2. No records in DB — process all items
3. Reverse items (oldest first)
4. Insert all

**Flow 2 — Subsequent polling (records exist):**
1. Fetch RSS feed (latest first)
2. Fetch `guid` of last record in DB (most recent article)
3. Process RSS items until matching `guid` is found — those are new items
4. If no new items found → stop
5. Reverse new items (oldest first)
6. Insert

## Ingest Scheduling
- **APScheduler** — used to schedule the daily RSS ingest job. Chosen over Celery for simplicity: no separate broker or worker process needed.
- Runs once per day inside the FastAPI process.
- No explicit monitoring — successful ingest is observable from new blog rows in DB. Errors logged.

## Auth (Google OAuth)
- Full server-side OAuth flow — no token exposure to client
- Server generates and stores `state` token before redirecting to Google
- On callback, server verifies `state`, exchanges `code` for access token
- JWT issued on successful login, stored in httpOnly cookie (safe from XSS, stateless)
- JWT payload: `user_id` only — minimal, no sensitive data exposed
- JWT expiry: 2 hours — no silent refresh, user is forced to log in again on expiry
- Name and avatar fetched from DB using `user_id` when needed
- Email stored in DB only — for future allowlist-based access control

## Caching
- Redis for caching layer
- RedisInsight for inspecting cache during development — runs as a Docker service, accessible at `http://localhost:5540`
- `@cache.cached` decorator on DAO methods for transparent cache handling
- DAO methods accept a `use_cache: bool = True` parameter — when `False`, cache is bypassed and DB is hit directly
- `use_cache` is decided by the handler (not the controller) based on business logic — e.g., after a staleness check, handler calls the service with `use_cache=False` to force a DB read
- Handler passes `use_cache` to service, service passes it to DAO

## Swagger UI (`/docs`)
- Protected with HTTP Basic Auth (username + password) in production
- JWT not required — `/docs` is a developer tool, not user-facing

## Rate Limiting
- No rate limiting — all LLM-generated content (summary, simplify, prerequisites) is cached per article or topic and shared across all users. First request pays the LLM cost; all subsequent requests are served from cache.

## Configuration

- All environment variables are accessed exclusively through `config.py` at project root — no module reads `os.environ` directly.
- `config.py` defines a `Config` class that uses `load_dotenv` to load `.env.local` and exposes all vars as typed attributes.
- Every module that needs a config value imports `Config` from `config.py`.

## Local Development
- Docker based — all services run via Docker Compose: `app`, `postgresql`, `pgadmin`, `redis`, `redisinsight`
- Postgres image: `pgvector/pgvector:pg16` — pgvector is an extension, not a separate service
- `docker-compose.yml` has no `env_file` — env vars are injected via `docker-compose.override.yml`
- `docker-compose.override.yml` is gitignored and placed manually on each machine — uses `.env.local` locally, `.env.prod` on production
- `docker compose up -d` works on both environments — no extra flags needed

## Deployment
- Digital Ocean — single Droplet ($12/month, 2 vCPU, 2GB RAM), upgrade to $24 (4GB RAM) if needed
- All services run via docker-compose on the same Droplet — no managed DB or separate services

## ORM and Database Access

- **SQLAlchemy** — ORM for all database access. DAOs use `Session` injected via FastAPI's `Depends(get_db)`.
- **pgvector-sqlalchemy** (`pgvector.sqlalchemy`) — SQLAlchemy integration for the `Vector` column type and pgvector operators (`<=>` cosine distance). Used in `TagDAO.find_similar` and `PrerequisiteDAO.find_similar`.
- Raw SQL via `text()` for hybrid search (keyword + vector + RRF CTE) — SQLAlchemy ORM is insufficient for this query shape.

---

## Frontend Data Loading
- `GET /` — FastAPI route, returns HTML shell (no blog data)
- On page load, Alpine.js fires AJAX call to `GET /api/blogs` to fetch blog data and render cards
- On filter/paginate, Alpine.js fires AJAX call with relevant params — cards update in place, no full page reload
- URL updated via `history.pushState` on filter/paginate for shareability
- Full page reload approach (server-side rendering on every interaction) was considered but rejected — slower UX, re-renders entire HTML on every filter/paginate action

## Vector DB

**Decision: pgvector**

- Postgres extension — no extra service, no extra memory footprint, fits on a single Droplet
- Qdrant ruled out: separate service, higher memory usage (observed to be problematic on self-hosted setups)
- Corpus size (hundreds to low thousands of articles) is well within pgvector's range
- Hybrid search implemented as a single SQL query — tsvector keyword + pgvector similarity, RRF fusion via CTE (no app-side merging needed)
- RRF formula: `1 / (60 + rank)` summed across keyword and vector result lists — standard formula from Cormack et al. 2009, k=60 is the canonical default

## Search & Embeddings

**SearchDAO and SearchService class design — resolved. See `docs/dao_and_service_class_design.md`.**
- RSS content is chunked at ingest — each chunk embedded and stored in `blog_chunk` table (`blog_id`, `chunk_text`, `embedding vector(1536)`) via pgvector
- Chunk-level embeddings chosen over a single per-article embedding — more precise semantic recall for specific concepts buried in long articles
- Limited tier articles (< 150 words) are excluded from chunking/embedding and never appear in semantic search
- Hybrid search uses RRF (Reciprocal Rank Fusion) to combine keyword and semantic ranked results — implemented as a single SQL CTE, no app-side fusion
- **Note:** Once data is ingested, test search via shell before wiring to the API — verify keyword, semantic, and RRF fusion results independently

## Chunking
- RSS content used as-is — no article scraping. Content tiers handle RSS content length variation.
- Strip HTML tags via BeautifulSoup (already in stack for og:image scraping) → plain text. Safe to run unconditionally — harmless on plain text, handles HTML content without conditional logic.
- If content is within token limit (~512 tokens) → embed directly as a single vector, skip chunking
- If content exceeds token limit → chunk with `RecursiveCharacterTextSplitter` from `langchain-text-splitters` (standalone package, not full LangChain), then embed each chunk
- Limited tier articles (< 150 words) are excluded from search and never reach the chunker/embedder

## Pydantic Schemas

All API request/response schemas are documented in `docs/api_contracts.md`. Key decisions:

- All responses use a shared `APIResponse[T]` envelope (`schemas.py` at project root) — `success`, `data`, `error` fields always present
- Each module owns its own schemas in `module/schemas.py` — no shared inheritance across modules
- `ContentTier` enum lives in `blog/schemas.py` — `LIMITED`, `PARTIAL`, `FULL`
- Summary and simplify responses nest `BlogItem` inside `SummaryDetail`/`SimplifyDetail` — blog and content are separate keys, not flat

---

## Handler Design

All handler class designs are documented in `docs/handler_design_guide.md`. Key decisions:

- `search/` has no handler or controller — search is routed entirely through `BlogHandler`
- Guest keyword search goes through `BlogService.list_blogs(keyword=...)` — no `SearchService` involved
- Signed-in hybrid search: `BlogHandler._hybrid_search` embeds query inline, calls `SearchService.keyword_search` + `SearchService.vector_search`, then `BlogHandler._reciprocal_rank_fusion` applies RRF formula
- Search results returned in full in one response — frontend paginates locally. Result cap: `SEARCH_RESULT_LIMIT = 30` (defined in `constants.py`)

---

## RSSClient (`rss_client.py`)

Two methods used across ingest and on-demand handlers:

- `get_feed(feed_url: str) -> list[dict]` — fetches and parses the RSS feed, returns all items (latest first). Each item contains guid, title, link, published_at, word_count, and raw content fields.
- `get_content(feed_url: str, guid: str) -> str` — fetches the RSS feed and extracts the article text for the item matching the given guid. Returns content from `<content:encoded>` or `<description>` — no scraping of the article URL.

---

## Summary Button (User-facing)
- On-demand LLM call — content fetched from RSS feed on first request, not stored in DB
- Cache result after first call — subsequent clicks by any user return cached response (no additional LLM call)
- Same caching approach applies to ELI5
- Cache eviction policy: TTL (7 days)
- Caching strategy: Cache Aside. Lookup order: cache → DB → LLM
  - Cache hit: return directly
  - Cache miss → `@cache.cached` fetches from DB, returns result → handler checks `updated_at`
    - `updated_at` within 7 days: return result (decorator writes back to cache)
    - `updated_at` older than 7 days: call LLM, update DB + cache
  - Cache miss, DB miss (first ever request): call LLM, create DB record, write to cache

## Tags
- Generated at ingest time via LLM
- Stable once set — not regenerated on a schedule
- Stability is intentional: tag-based URLs (e.g., `/?tag=databases`) should remain consistent for users
- **Normalization pipeline:** string normalize (lowercase, strip, collapse hyphens/underscores/spaces to `-`) → embed via `Embedder.embed()` → cosine similarity check against existing tags in DB (threshold: 0.95) → use existing `tag_id` or insert new tag
- **Embedding timing:** embedding is computed inline at ingest and stored in the same insert as the tag name — there is no separate embedding step. `create_tag(name, embedding)` writes both together.
- `tag` table stores `embedding vector(1536)` — used only for normalization at ingest, not for search
- Threshold tuning deferred to evaluation stage — err on the side of fragmentation over false merge

## Prerequisites
- Topic names extracted at ingest time via LLM — stored in `prerequisite` table (UNIQUE per topic name), linked to blogs via `blog_prerequisite` junction table
- **Normalization pipeline:** embed extracted topic name via `Embedder.embed()` → cosine similarity check against existing prerequisites in DB (threshold: 0.95) → use existing `prerequisite_id` or insert new prerequisite
- **Embedding timing:** embedding is computed inline at ingest and stored in the same insert as the topic name — there is no separate embedding step. `create_prerequisite(topic_name, embedding)` writes both together.
- `prerequisite` table stores `embedding vector(1536)` — used only for normalization at ingest, not for search
- Explanation (primer + deep dive) generated on-demand when user clicks a topic chip — single LLM call returns both
- Caching: keyed by `topic_name` — one cached entry per topic, shared across all articles and users. Lookup order: cache → DB → LLM
- Refresh: configurable interval (default 7 days) — periodic regeneration intentional, newer LLM calls may produce better results
- No rate limiting — cache amortizes cost

## Search Behaviour
- Search always runs across all sources — no combined source + search filtering at the API level
- When a user starts typing in the search bar, the source filter is cleared automatically by the frontend
- Helper text shown below search bar when source filter was active: "Searching across all companies"
- `search_by_keyword` excludes limited tier articles — enforced in SQL at the DAO level (`WHERE word_count >= 150`)

---

## Return Types

- **DAO methods** — return SQLAlchemy ORM model instances (e.g. `Blog`, `User`, `Tag`) or `list[Model]`. Return `None` when a record is not found.
- **Service methods** — pass ORM models through unchanged. Same return types as DAO.
- **Handler methods** — convert ORM models to Pydantic schemas. Return `APIResponse[T]` instances. Conversion happens here, never in DAO or service.

---

## LLM Best Practices

- **Structured output** — all prompts request strict JSON-only responses. Enforced at two levels: system prompt instructs JSON-only, and API-level `response_format: json_object` where supported.
- **Timeout** — `call_llm()` in `utils.py` accepts a `timeout` parameter (seconds). Default: 30 seconds, defined in `config.py`. On timeout, raises `LLMUnreachableError` → 502.
- **Idempotent ingest** — `blog.id` is the RSS `guid` and serves as the PK. Duplicate inserts are prevented by the PK constraint — no separate UNIQUE constraint needed.

---

## Error Handling

Custom exceptions live in `exceptions.py` at project root.

```python
class DatabaseError(Exception): ...       # DAO layer — wraps SQLAlchemy exceptions
class UnauthorizedError(Exception): ...   # No valid JWT present
class AuthError(Exception): ...           # OAuth flow failure (bad state, not in allowlist, etc.)
class ForbiddenError(Exception): ...      # Content tier check failed
class NotFoundError(Exception): ...       # Record not found
class RSSFeedError(Exception): ...        # RSS feed unavailable
class LLMUnreachableError(Exception): ... # LLM call failed
```

**Layer responsibilities:**
- **DAO** — catches SQLAlchemy exceptions, re-raises as `DatabaseError`
- **Handler** — raises business logic exceptions (`NotFoundError`, `ForbiddenError`, `AuthError`, `UnauthorizedError`, `RSSFeedError`, `LLMUnreachableError`). Lets `DatabaseError` propagate.
- **Controller** — catches all exceptions, converts to `APIResponse(success=False, data=None, error=ErrorDetail(code=..., message=...))` with appropriate HTTP status code

**HTTP status code mapping:**
| Exception | Status |
|-----------|--------|
| `DatabaseError` | 500 |
| `UnauthorizedError` | 401 |
| `AuthError` | 401 |
| `ForbiddenError` | 403 |
| `NotFoundError` | 404 |
| `RSSFeedError` | 502 |
| `LLMUnreachableError` | 502 |

---

## Observability — Arize Phoenix

**Decision: Arize Phoenix for LLM observability and in-system evals.**

Phoenix is an observability-first tool — traces every LLM call via OpenTelemetry, then runs evals on top of those traces. Chosen over Braintrust (eval-only) because it covers both production monitoring and eval in one tool.

**Deployment:** Self-hosted Docker service — runs in `docker-compose.yml` alongside all other services (both dev and prod). Phoenix UI accessible at `http://localhost:6006`. OTLP HTTP endpoint: `http://phoenix:4318/v1/traces` (internal Docker network). `arize-phoenix` full server runs in Docker — app only needs the thin client packages.

**Integration is part of v1** — not deferred. Tracing starts from the first ingest run.

**What gets traced:**
- Ingest pipeline — tag + prerequisite extraction LLM call (`call_llm()` in `IngestHandler`) — auto-instrumented
- Ingest pipeline — normalization decision per candidate tag/prerequisite — custom OTel spans in `_process_tag` and `_process_prerequisite` (see below)
- Summary generation — `call_llm()` in `SummaryHandler` — auto-instrumented
- Simplify (ELI5) generation — `call_llm()` in `SimplifyHandler` — auto-instrumented
- Prerequisite explanation generation — `call_llm()` in `PrerequisiteHandler` — auto-instrumented

**Integration approach:**
- `openinference-instrumentation-anthropic` — auto-instruments all Anthropic SDK calls. Initialized once at module level in `app.py`. `call_llm()` in `utils.py` needs no changes.
- Custom spans in `ingest/handler.py` — `tracer = trace.get_tracer("enggsystemfeed.ingest")` at module level. One span per candidate tag/prerequisite.
- Each auto-trace includes: model, prompt, response, latency, token count

**Normalization span attributes (tag.normalize / prerequisite.normalize):**
| Attribute | Type | Notes |
|-----------|------|-------|
| `tag.candidate` | str | Raw LLM output |
| `tag.normalized` | str | After lowercase/strip/collapse to `-` |
| `tag.similarity_score` | float | Cosine similarity vs. closest existing; None if DB empty |
| `tag.action` | str | `"merge"` or `"insert"` |
| `tag.canonical` | str | Existing item it merged into (merge only) |

Same attributes prefixed `prerequisite.*` for prerequisite spans.

**In-system evals:**
- Phoenix runs LLM-as-judge evals on production traces — e.g. flag summaries that are too short, tags that are too broad
- Evals run asynchronously against stored traces — no impact on request latency
