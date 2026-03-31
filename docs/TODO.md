# Implementation TODO

## Pre-conditions

- [x] **SQLAlchemy ORM models location** — per-module `models.py` (e.g., `auth/models.py`, `blog/models.py`)
- [x] **Chunker and Embedder class signatures** — defined and implemented in `ingest/chunker.py` and `ingest/embedder.py`
- [x] **Embedding model** — `text-embedding-3-small` (1536 dimensions)
- [x] **LLM model** — `claude-sonnet-4-6`
- [x] **Ingest prompt** — finalised and in `prompts/ingest.py`
- [x] **Query embedding approach** — inline in `BlogHandler._hybrid_search` via `Embedder.embed()`
- [x] **Templates/static files location** — `templates/index.html`, static files in `static/`

---

## Agent: Infra

### Tasks

- [x] **Create `Dockerfile`**
- [x] **Create `docker-compose.yml`**
- [x] **Create `docker-compose.override.yml`**
- [x] **Create `.gitignore`**

### ✅ Checkpoint 1 — Infra

- [x] `docker compose up -d` completes without errors
- [x] All 6 containers are running
- [x] PostgreSQL reachable via pgadmin at `http://localhost:5050`
- [x] Redis reachable — RedisInsight at `http://localhost:5540` confirmed
- [x] App container starts — `http://localhost:8000` responds
- [x] Phoenix UI reachable at `http://localhost:6006`

---

## Agent: Database

### Tasks

- [x] **Install and initialise Alembic**
- [x] **Create initial migration** — pgvector extension + all 11 tables, UUID PKs, composite PKs, UNIQUE constraints

### ✅ Checkpoint 2 — Database

- [x] `alembic upgrade head` runs without errors
- [x] All 11 tables exist
- [x] `vector` extension enabled
- [x] `blog_chunk.embedding`, `tag.embedding`, `prerequisite.embedding` are `vector(1536)`
- [x] Composite PKs on `blog_tag` and `blog_prerequisite`
- [x] `topic_name` UNIQUE on `prerequisite`, `tag` UNIQUE on `tag`

---

## Agent: Backend

### Core files

- [x] **`config.py`**
- [x] **`constants.py`**
- [x] **`exceptions.py`**
- [x] **`schemas.py`**
- [x] **`database.py`** — includes `Cache` class with `@cache.cached` and `@cache.set` decorators
- [x] **`utils.py`**
- [x] **`rss_client.py`**
- [x] **`app.py`**

### ✅ Checkpoint 3 — Backend core files

- [x] App container starts without import errors
- [x] `http://localhost:8000/docs` accessible and protected by HTTP Basic Auth
- [x] `GET /` returns HTML response

---

### ORM Models

- [x] All models implemented in per-module `models.py` files

---

### `auth/` module

- [x] **`auth/schemas.py`**
- [x] **`auth/dao.py`**
- [x] **`auth/service.py`**
- [x] **`auth/utils.py`**
- [x] **`auth/client.py`**
- [x] **`auth/handler.py`**
- [x] **`auth/controller.py`**

### ✅ Checkpoint 4 — Auth module

- [x] `GET /auth/initiate` — returns auth URL, frontend redirects to Google
- [x] Complete Google sign-in flow — callback succeeds, JWT cookie set
- [x] `GET /auth/me` with JWT cookie — returns `user_id`, `name`, `profile_url`
- [x] `GET /auth/me` without JWT cookie — returns 401
- [x] `POST /auth/logout` — clears JWT cookie
- [x] User row exists in `user` table
- [x] Email not in `allowed_users` — rejected with 401

---

### `blog/` module

- [x] **`blog/schemas.py`**
- [x] **`blog/dao.py`**
- [x] **`blog/service.py`**
- [x] **`blog/handler.py`**
- [x] **`blog/controller.py`**

---

### `tags/` module

- [x] **`tags/dao.py`**
- [x] **`tags/service.py`**

---

### `search/` module

- [x] **`search/dao.py`**
- [x] **`search/service.py`**

### ✅ Checkpoint 5 — Blog, Tags, Search modules

- [x] `GET /api/v1/sources` — returns list of blog sources
- [x] `GET /api/v1/blogs` — returns paginated blog list
- [x] `GET /api/v1/blogs?source=<name>` — filters by source
- [x] `GET /api/v1/blogs?page=2&count=5` — pagination works
- [x] `GET /api/v1/blogs?search=<keyword>` as guest — keyword results
- [x] `GET /api/v1/blogs?search=<keyword>` as signed-in — hybrid search results
- [x] Signed-in response includes `tags` and `prerequisites` arrays
- [x] Guest response has empty `tags` and `prerequisites`
- [x] `content_tier` computed correctly from `word_count`

---

### `summary/` module

- [x] **`summary/schemas.py`**
- [x] **`summary/dao.py`** — `@cache.cached` on read, `@cache.set` on write
- [x] **`summary/service.py`**
- [x] **`summary/handler.py`**
- [x] **`summary/controller.py`**

---

### `simplify/` module

- [x] **`simplify/schemas.py`**
- [x] **`simplify/dao.py`** — `@cache.cached` on read, `@cache.set` on write
- [x] **`simplify/service.py`**
- [x] **`simplify/handler.py`**
- [x] **`simplify/controller.py`**

### ✅ Checkpoint 6 — Summary and Simplify modules

- [x] `GET /api/v1/blogs/{blog_id}/summary` as signed-in — returns summary
- [x] Call again — served from cache (verified in RedisInsight)
- [x] `summary` row exists in DB with `updated_at` set
- [x] Cache entry visible in RedisInsight
- [x] As guest — returns 401
- [x] `LIMITED` tier blog — returns 403
- [x] `GET /api/v1/blogs/{blog_id}/simplify` as signed-in with `FULL` tier — returns ELI5
- [x] `PARTIAL` tier — returns 403
- [x] `LIMITED` tier — returns 403

---

### `prerequisites/` module

- [x] **`prerequisites/schemas.py`**
- [x] **`prerequisites/dao.py`** — `@cache.cached` on read, `@cache.set` on write
- [x] **`prerequisites/service.py`**
- [x] **`prerequisites/handler.py`**
- [x] **`prerequisites/controller.py`**

### ✅ Checkpoint 7 — Prerequisites module

- [x] `GET /api/v1/prerequisites/{topic_name}` as signed-in — returns definition, why_it_matters, example, deep_dive
- [x] Call again — served from cache (verified in RedisInsight)
- [x] `prerequisite` row in DB updated with all 4 fields
- [x] Cache entry visible in RedisInsight
- [x] As guest — returns 401
- [x] Response shape matches `docs/api_contracts.md`

---

### `ingest/` module

- [x] **`ingest/chunker.py`**
- [x] **`ingest/embedder.py`**
- [x] **`ingest/handler.py`**

### ✅ Checkpoint 8 — Ingest module

- [x] Ingest runs without errors
- [x] New rows in `blog` table
- [x] `blog_chunk` rows exist with non-null embeddings
- [x] `tag` and `blog_tag` rows exist
- [x] `prerequisite` and `blog_prerequisite` rows exist
- [x] `thumbnail` populated where og:image found, NULL otherwise
- [x] Second ingest run produces no duplicate `blog` rows
- [x] `GET /api/v1/blogs` returns real ingested articles with tags and prerequisites
- [x] Hybrid search returns sensible results for signed-in user

---

### `prompts/` module

- [x] **`prompts/summary.py`**
- [x] **`prompts/simplify.py`**
- [x] **`prompts/prerequisites.py`**
- [x] **`prompts/ingest.py`**

---

## Agent: Frontend

- [x] **HTML shell** — navbar, feed row, blog card grid, modals, pagination, empty state
- [x] **On page load** — `GET /auth/me`, `GET /api/v1/sources`, `GET /api/v1/blogs`
- [x] **Company filter dropdown**
- [x] **Search bar**
- [x] **Blog card** — thumbnail, title, prerequisites chips, tags chips, Summary/Simplify buttons, content tier logic
- [x] **Pagination**
- [x] **Empty state**
- [x] **Summary page**
- [x] **Simplify page**
- [x] **Prerequisites modal**
- [x] **Sign In modal** — fetch `/auth/initiate`, redirect to Google
- [x] **Ad slots**
- [x] **CSS extracted to `static/css/style.css`**
- [x] **JS extracted to `static/js/app.js`**

### ✅ Checkpoint 9 — Frontend (full E2E)

**As a guest:**
- [x] Feed loads with blog cards
- [x] Company filter dropdown shows all sources
- [x] Selecting a company filters the feed, URL updates
- [x] Keyword search returns results, source filter clears
- [x] Pagination works
- [x] Blog card thumbnail and title open original article in new tab
- [x] Summary + Simplify buttons clicking shows Sign In modal
- [x] Tags and prerequisites hidden on cards
- [x] Limited tier card shows badge, no Summary/Simplify buttons
- [x] Partial tier card shows Summary button only

**Signing in:**
- [x] "Sign in with Google" initiates OAuth flow
- [x] After sign-in, navbar shows avatar + name + Sign Out
- [x] Refreshing page keeps user signed in
- [x] Sign Out clears session

**As a signed-in user:**
- [x] Feed cards show tags and prerequisites chips
- [x] Max 3 tags/prerequisites with "+N more"
- [x] Clicking tag filters feed by tag, URL updates
- [x] Clicking prerequisite chip opens prerequisites modal
- [x] Prerequisites modal shows primer by default
- [x] "Read more" reveals deep dive
- [x] Modal closes on Esc or click outside
- [x] Summary button navigates to summary page
- [x] Summary page shows all required fields
- [x] Simplify page shows correct content
- [x] Cache serves repeated requests instantly
- [x] Hybrid search returns semantically relevant results
