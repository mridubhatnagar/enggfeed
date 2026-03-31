# Before You Start — Your Action Items

Complete all of these before running any agent.

---

## 0. Run evals first (before any agent)

Do this before implementing anything. Outcomes feed directly into the system.

**Phase 1 — Tag + prerequisite quality eval:**
- [x] Write ingest prompt in `eval/phase1_generate.py`
- [x] Fill `eval/.env` with `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `BRAINTRUST_API_KEY`
- [x] Run `python eval/phase1_generate.py` — fetches Cloudflare + GitHub RSS, calls Claude, writes `eval/phase1_results.json`, uploads to Braintrust
- [x] Label each row in Braintrust UI (`ok` / `too_broad`)
- [x] Check GPT-4.1 scorer agreement in Braintrust — if ok rate is low, tweak prompt in `phase1_generate.py` and re-run
- [x] Once satisfied, export labeled dataset from Braintrust → save as `eval/phase1_labeled_export.json`
- [x] Run `python eval/phase1_export_seeds.py` → generates `eval/seed_tags.json` + `eval/seed_prerequisites.json`
- [x] Lock the Claude prompt — copy final version into `prompts/ingest.py` when that stub is created

**Phase 2 — Similarity threshold eval:**
- [x] Update `eval/phase2_similarity.py` to handle both tags and prerequisites
- [x] Run `python eval/phase2_similarity.py` — embeds seed tags + prerequisites, fetches Meta + AWS + Slack RSS, writes `eval/phase2_similarity.json`
- [x] Fill `feedback: "merge"` or `"separate"` for each row in `phase2_similarity.json`
- [x] Pick threshold where merge/separate decisions look right — `TAG_SIMILARITY_THRESHOLD = 0.88` (configurable via env var, default in `config.py`)

**Seed list insertion (before first ingest):**
- [x] Write a one-off script or use psql to embed + insert `seed_tags.json` into the `tag` table
- [x] Write a one-off script or use psql to embed + insert `seed_prerequisites.json` into the `prerequisite` table

---

## 1. Decisions to make

Resolve these before starting the relevant agent. Do not leave them to the agent to decide.

- [x] **SQLAlchemy ORM models location** — per-module `models.py` (e.g. `auth/models.py`, `blog/models.py`). Agent files updated.
- [x] **LLM model** — `claude-sonnet-4-6` confirmed.
- [x] **Embedding model** — `text-embedding-3-small` via OpenAI SDK. Agent files updated.
- [x] **Query embedding approach** — `embed_text(text: str) -> list[float]` added to `utils.py`. `BlogHandler._hybrid_search` imports and calls it. Agent files updated.
- [x] **Chunker class signature** — `Chunker(max_tokens: int = 512)` with `chunk(text: str) -> list[str]`. Agent files updated.
- [x] **Embedder class signature** — `Embedder()` with `embed(text: str) -> list[float]`. Single embedding only. Agent files updated.
- [x] **Templates/static files location** — `templates/index.html` (served via `FileResponse`), `static/` (CSS, JS, images via `StaticFiles`). No Jinja2. Agent files updated.

---

## 2. Files to create manually

- [x] **`requirements.txt`** — create at project root before running the `infra` agent (Dockerfile installs from it).

  Dependencies needed:
  ```
  fastapi
  uvicorn
  sqlalchemy
  alembic
  psycopg2-binary
  pgvector
  pydantic
  pydantic-settings
  redis
  python-jose
  feedparser
  beautifulsoup4
  requests
  anthropic       # LLM (claude-sonnet-4-6)
  openai          # embeddings (text-embedding-3-small)
  ```

- [x] **`docker-compose.override.yml`** — create at project root before running `docker compose up`. Not checked into git. Example:

  ```yaml
  services:
    app:
      env_file: .env.local
    postgresql:
      env_file: .env.local
    pgadmin:
      env_file: .env.local
    redis:
      env_file: .env.local
    redisinsight:
      env_file: .env.local
  ```

- [x] **`.env.local`** — create at project root alongside `docker-compose.override.yml`. Required vars:

  | Variable | Example / Note |
  |---|---|
  | `DATABASE_URL` | `postgresql://user:password@postgresql:5432/enggsystemfeed` |
  | `REDIS_URL` | `redis://redis:6379` |
  | `JWT_SECRET` | any strong random string |
  | `GOOGLE_CLIENT_ID` | from Google Cloud Console |
  | `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
  | `GOOGLE_REDIRECT_URI` | `http://localhost:8000/auth/callback` |
  | `POSTGRES_USER` | for postgresql container |
  | `POSTGRES_PASSWORD` | for postgresql container |
  | `POSTGRES_DB` | for postgresql container |
  | `PGADMIN_DEFAULT_EMAIL` | for pgadmin container |
  | `PGADMIN_DEFAULT_PASSWORD` | for pgadmin container |
  | `SWAGGER_USERNAME` | for `/docs` Basic Auth |
  | `SWAGGER_PASSWORD` | for `/docs` Basic Auth |
  | `ANTHROPIC_API_KEY` | for Claude (LLM calls) |
  | `OPENAI_API_KEY` | for text-embedding-3-small (embeddings) |
  | `PHOENIX_ENDPOINT` | `http://phoenix:4318/v1/traces` |

---

## 3. Prompts to write and eval

All four prompts are finalized in `docs/prompts.md`. The `backend-prompts` agent will copy them directly — no manual eval needed post-agent.

- [x] **`prompts/ingest.py`** — finalized (copied from `eval/phase1_generate.py` v4)
- [x] **`prompts/summary.py`** — finalized in `docs/prompts.md`
- [x] **`prompts/simplify.py`** — finalized in `docs/prompts.md`
- [x] **`prompts/prerequisites.py`** — finalized in `docs/prompts.md`

---

## 4. Google OAuth setup

- [x] Create a project in Google Cloud Console
- [x] Enable the Google OAuth 2.0 API
- [x] Add `http://localhost:8000/auth/callback` as an authorised redirect URI
- [x] Copy Client ID and Client Secret into `.env.local`
