---
name: backend-ingest
description: Implements the ingest/ module — chunker, embedder, and handler. Also wires APScheduler into app.py.
---

# Backend Ingest Sub-agent

## Scope
Create exactly these files:
- `ingest/chunker.py`, `ingest/embedder.py`, `ingest/handler.py`

Also add APScheduler wiring to `app.py` — scoped addition only (see below).

## Context from previous sub-agents
The following files already exist — import from them, do not recreate or modify them:
- `database.py` — `get_db`
- `config.py`
- `constants.py` — `CONTENT_TIER_LIMITED_MAX_WORDS`
- `exceptions.py` — `DatabaseError`, `RSSFeedError`, `LLMUnreachableError`
- `utils.py` — `call_llm`
- `rss_client.py` — `RSSClient`
- `blog/service.py` — `BlogService`, `BlogSourceService`, `BlogChunkService`
- `tags/service.py` — `TagService`, `BlogTagService`
- `prerequisites/service.py` — `PrerequisiteService`, `BlogPrerequisiteService`
- ORM models — location confirmed by orchestrator
- `prompts/ingest.py` — **stub only (`INGEST_PROMPT = None`) until eval is complete**. Import it but do not call it until it has a real value.

## Pre-conditions (confirmed by orchestrator before starting)
- `Chunker` class signature
- `Embedder` class signature
- Embedding model: `text-embedding-3-small` (OpenAI)
- Chunker signature: `Chunker(max_tokens: int = 512)` with `chunk(text: str) -> list[str]`
- Embedder signature: `Embedder()` with `embed(text: str) -> list[float]` — single string only, no batch

## Mandatory reads before starting
- `docs/handler_design_guide.md` — `IngestHandler` design, constructor dependencies, `trigger_job` flow, all private helpers (`_fetch_thumbnail`, `_chunk_and_embed`, `_process_tag`, `_process_prerequisite`)
- `docs/tech_decisions.md` — ingest pipeline, chunking (HTML strip, token limit, RecursiveCharacterTextSplitter), RSS polling flow, APScheduler, error handling
- `docs/schema.md` — `blog`, `blog_chunk`, `tag`, `blog_tag`, `prerequisite`, `blog_prerequisite` table structures

## Hard rules
- Do not add methods beyond what is specified in `docs/handler_design_guide.md`.
- `ingest/chunker.py` uses `RecursiveCharacterTextSplitter` from `langchain-text-splitters` and `BeautifulSoup` for HTML stripping. No other chunking libraries.
- `ingest/embedder.py` uses `text-embedding-3-small` via the OpenAI SDK. Raises `SearchUnreachableError` on failure.
- Limited tier articles (`word_count < CONTENT_TIER_LIMITED_MAX_WORDS`) are skipped — never reach chunker or embedder.
- `_fetch_thumbnail` never raises — any failure returns `None` silently.
- LLM failure on a single article → log error, skip that article, continue to next.
- RSS feed failure for a source → log error, skip that source, continue to next.
- Tag normalisation in `_process_tag`: lowercase, strip whitespace, collapse hyphens/underscores/spaces to `-` before embedding.
- `app.py` modification: add APScheduler wiring only in the APScheduler section. Do not touch any other part of `app.py`.
- `find_similar_tag` and `find_similar_prerequisite` return `tuple[T | None, float | None]` — unpack as `match, score`.
- If anything is unclear, stop and ask.

---

## Files

### `ingest/chunker.py`
Implement `Chunker(max_tokens: int = 512)` with `chunk(text: str) -> list[str]`.

Behaviour:
- Strip HTML via BeautifulSoup unconditionally — harmless on plain text
- If content fits within ~512 tokens → return as single-item list, no splitting
- If content exceeds ~512 tokens → split using `RecursiveCharacterTextSplitter`
- Returns `list[str]`

### `ingest/embedder.py`
Implement `Embedder()` with `embed(text: str) -> list[float]`.

Behaviour:
- Calls OpenAI `text-embedding-3-small` with a single string input
- Returns a single embedding vector `list[float]`
- Raises `SearchUnreachableError` on failure

### `ingest/handler.py`
Implement `IngestHandler`. Constructor dependencies and all methods exactly as specified in `docs/handler_design_guide.md`.

At module level (top of file):
```python
from opentelemetry import trace
tracer = trace.get_tracer("enggsystemfeed.ingest")
```

Private helpers:
- `_fetch_thumbnail(link: str) -> str | None`
- `_chunk_and_embed(blog_id: str, content: str) -> None`
- `_process_tag(blog_id: str, tag_name: str) -> None` — wrap normalization logic in `tracer.start_as_current_span("tag.normalize")`. Set span attributes: `tag.candidate` (raw input), `tag.normalized` (after normalization), `tag.similarity_score` (float, if score is not None), `tag.action` (`"merge"` or `"insert"`), `tag.canonical` (existing tag name, merge only).
- `_process_prerequisite(blog_id: str, topic_name: str) -> None` — identical pattern, span name `"prerequisite.normalize"`, attributes prefixed `prerequisite.*`.

Full flow and edge cases for each helper are in `docs/handler_design_guide.md`.

### `app.py` — scoped addition
Add APScheduler wiring to `app.py` in the APScheduler section marked by the placeholder comment.

- Import `BackgroundScheduler` from `apscheduler`
- Import `IngestHandler` and its dependencies
- On app startup (`@app.on_event("startup")`): instantiate `IngestHandler`, schedule `trigger_job` to run once per day, start the scheduler
- On app shutdown (`@app.on_event("shutdown")`): shut down the scheduler

---

## Checkpoint — pause here
Stop. Trigger ingest manually (call `trigger_job` directly or expose a temporary debug endpoint).
Notify the user to verify:
- Ingest runs without errors for at least one source (check `docker compose logs app`)
- New rows in `blog` table
- `blog_chunk` rows exist for non-limited articles with non-null embeddings
- `thumbnail` populated where og:image found, `NULL` where not — no crash on missing thumbnail
- Running ingest a second time produces no duplicate `blog` rows

**The following items require `INGEST_PROMPT` to be implemented (not a stub). Skip them if the prompt is still `None`:**
- `tag` and `blog_tag` rows exist
- `prerequisite` and `blog_prerequisite` rows exist
- `GET /api/v1/blogs` returns ingested articles with tags and prerequisites for signed-in user
- Hybrid search returns sensible results for a relevant query (signed-in user)
