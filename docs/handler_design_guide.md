# Handler Class Design Guide

## How to think about each handler

For each module, work through these five questions:

**1. What business rules does this module own?**
- What decisions does this handler make that no other layer should make?
- e.g., Summary handler: "is a refresh due?" (check `updated_at` vs 7 days), "does a summary already exist or do I generate fresh?"

**2. What services does it need to orchestrate?**
- Handlers are the only place where multiple services coordinate.
- List which services need to be injected via constructor.

**3. What is the happy path?**
- Step by step, what happens on a normal request?

**4. What are the edge cases / branching conditions?**
- e.g., cache hit vs miss, record exists vs not, user tier check, refresh due vs not

**5. What does it return?**
- Match this to the API contract for that module (`docs/api_contracts.md`).

---

## Order to design handlers (simpler → complex)

| Order | Module | Why |
|-------|--------|-----|
| 1 | `auth/` | OAuth flow, allowlist check, JWT issuance — foundational, everything else depends on JWT |
| 2 | `blog/` | Listing, filtering, pagination — no LLM, straightforward |
| 3 | `tags/` | No handler — services consumed by BlogHandler only |
| 4 | `summary/` | LLM + cache + refresh logic — establishes the pattern |
| 5 | `simplify/` | Same pattern as summary |
| 6 | `prerequisites/` | LLM + cache + refresh + junction table writes |
| 7 | `ingest/` | Pipeline orchestration — RSS → embed → tag → prerequisites |

---

## Rules to keep in mind

- Handlers call services only — never DAOs directly.
- Services are injected via constructor — handlers do not instantiate their own dependencies.
- Cross-service coordination lives here and nowhere else.
- Only handlers decide when to pass `use_cache=False` to bypass cache.
- Document each handler method with: inputs, services called, business rules applied, output.

---

## `auth/` Handler Design

### Supporting classes

**`AuthClient`** (`auth/client.py`)
- `get_auth_url(state: str) -> str` — builds the Google OAuth URL with client_id, redirect_uri, state, scopes
- `exchange_code(code: str) -> str` — calls Google's token endpoint with code + client credentials + redirect_uri, returns raw ID token
- `verify_id_token(id_token: str) -> dict` — verifies audience, checks `email_verified`, returns decoded claims

**`auth/utils.py`**
- `generate_jwt_token(user_id: int) -> str`
- `decode_jwt_token(token: str) -> dict` — lives in `auth/utils.py`; imported from there by all modules that need to verify JWT

---

### `AuthHandler`

**Constructor dependencies:**
- `auth_client: AuthClient`
- `user_service: UserService`
- `allowed_user_service: AllowedUserService`

---

#### `initiate(response: Response) -> str`
Happy path:
1. `create_and_store_state_token()` — generate state token, store in HttpOnly cookie
2. `auth_client.get_auth_url(state)` — build Google OAuth URL
3. Return URL to frontend

---

#### `callback(code: str, state: str, request: Request, response: Response) -> str`
Happy path:
1. `verify_state_token(state, request)` — compare query param against cookie; delete cookie after
2. `auth_client.exchange_code(code)` — call Google token endpoint, get ID token
3. `auth_client.verify_id_token(id_token)` — verify audience + `email_verified`, extract email + `google_auth_id`
4. `allowed_user_service.get_allowed_user_by_email(email)` — if None, reject
5. `user_service.get_user_by_auth_id(google_auth_id)` — check if returning user
6. If None → `user_service.create_user(...)` — insert new row
7. `generate_jwt_token(user_id)` — store in HttpOnly cookie
8. Return success

Edge cases:
- State mismatch → reject
- `email_verified` false → reject
- Email not in allowlist → reject

---

#### `me(request: Request) -> UserDetail`
Happy path:
1. `decode_jwt_token(token)` — extract `user_id` from JWT cookie
2. `user_service.get_user_by_id(user_id)` — fetch name, profile_url
3. Return to controller

---

## `blog/` Handler Design

### `BlogHandler`

**Constructor dependencies:**
- `blog_service: BlogService`
- `blog_source_service: BlogSourceService`
- `blog_tag_service: BlogTagService`
- `tag_service: TagService`
- `blog_prerequisite_service: BlogPrerequisiteService`
- `prerequisite_service: PrerequisiteService`

---

#### `get_blogs(sources: list[str] | None, tags: list[str] | None, page, count, request) -> PaginatedBlogs`
Happy path:
1. `decode_jwt_token(request)` — if JWT present, set `is_signed_in = True`
2. If `source` present → `blog_source_service.get_source_by_name(source)` → `source_id`
3. If `tag` present → `tag_service.get_tag_by_name(tag)` → `tag_id`
4. `blog_service.list_blogs(source_id, tag_id, page, count)` — DAO builds dynamic query based on present params
5. Compute `content_tier` for each blog from `word_count` (`limited` < 150, `partial` 150–300, `full` 300+)
6. If `is_signed_in`:
   - `blog_tag_service.list_tag_ids_by_blog_ids(blog_ids)` → tag_ids per blog
   - `tag_service.list_tags_by_ids(tag_ids)` → tag names
   - Filter to `partial` and `full` tier blog_ids only → `eligible_blog_ids`
   - `blog_prerequisite_service.list_prerequisite_ids_by_blog_ids(eligible_blog_ids)` → prerequisite_ids per blog
   - `prerequisite_service.list_prerequisites_by_ids(prerequisite_ids)` → prerequisite rows (topic names + ids)
   - Attach tags and prerequisites to each blog (prerequisites empty array for `limited` tier)
7. Return enriched list. Server-side pagination applies via `page` and `count`.

Edge cases:
- Guest user → tags and prerequisites are empty arrays
- `tag` param present but not found → empty result

---

#### `get_sources() -> list[BlogSource]`
Happy path:
1. `blog_source_service.list_all_sources()` → return list

---

## `summary/` Handler Design

### `SummaryHandler`

**Constructor dependencies:**
- `blog_service: BlogService`
- `blog_source_service: BlogSourceService`
- `summary_service: SummaryService`
- `blog_tag_service: BlogTagService`
- `tag_service: TagService`
- `blog_prerequisite_service: BlogPrerequisiteService`
- `prerequisite_service: PrerequisiteService`
- `rss_client: RSSClient`

---

#### `get_summary(blog_id: str, request: Request) -> SummaryDetail`
**Invariant:** A `summary` row is never created at ingest time. The `summary` table is populated only on first user request. Do not add any code path that assumes a `summary` row exists for a blog that has been ingested.

Happy path:
1. `decode_jwt_token(request)` — reject if no valid JWT
2. `blog_service.get_blog_by_blog_id(blog_id)` — fetch title, link, thumbnail, word_count, blog_source_id, guid
3. Compute `content_tier` from `word_count` — return `403` if `limited`
4. `summary_service.get_summary_by_blog_id(blog_id)` — cache → DB
5. `check_refresh_due(updated_at)` (from `utils.py`) — if stale or not found:
   - `blog_source_service.get_source_by_id(blog_source_id)` → feed_url
   - `rss_client.get_content(feed_url, guid)` → article text (extracted from RSS feed item — no scraping)
   - `call_llm(prompt + article text)` with prompt from `prompts/summary.py` — returns dict `{"short_summary": "...", "key_points": [...]}`
   - If stale → `summary_service.update_summary(blog_id, content)` — update DB, update cache
   - If not found → `summary_service.create_summary(blog_id, content)` — insert DB, write cache
6. `blog_tag_service.list_tag_ids_by_blog_ids([blog_id])` → tag_ids
7. `tag_service.list_tags_by_ids(tag_ids)` → tag names
8. `blog_prerequisite_service.list_prerequisite_ids_by_blog_ids([blog_id])` → prerequisite_ids
9. `prerequisite_service.list_prerequisites_by_ids(prerequisite_ids)` → topic names
10. Return response

Edge cases:
- No JWT → reject
- `content_tier` is `limited` → `403`
- RSS feed unavailable → propagate error

---

## `simplify/` Handler Design

### `SimplifyHandler`

**Constructor dependencies:**
- `blog_service: BlogService`
- `blog_source_service: BlogSourceService`
- `simplify_service: SimplifyService`
- `blog_tag_service: BlogTagService`
- `tag_service: TagService`
- `blog_prerequisite_service: BlogPrerequisiteService`
- `prerequisite_service: PrerequisiteService`
- `rss_client: RSSClient`

---

#### `get_simplify(blog_id: str, request: Request) -> SimplifyDetail`
**Invariant:** A `simplify` row is never created at ingest time. The `simplify` table is populated only on first user request. Do not add any code path that assumes a `simplify` row exists for a blog that has been ingested.
Happy path:
1. `decode_jwt_token(request)` — reject if no valid JWT
2. `blog_service.get_blog_by_blog_id(blog_id)` — fetch title, link, thumbnail, word_count, blog_source_id, guid
3. Compute `content_tier` from `word_count` — return `403` if `limited` or `partial`
4. `simplify_service.get_simplify_by_blog_id(blog_id)` — cache → DB
5. `check_refresh_due(updated_at)` (from `utils.py`) — if stale or not found:
   - `blog_source_service.get_source_by_id(blog_source_id)` → feed_url
   - `rss_client.get_content(feed_url, guid)` → article text (extracted from RSS feed item — no scraping)
   - `call_llm(prompt + article text)` with prompt from `prompts/simplify.py`
   - If stale → `simplify_service.update_simplify(...)` — update DB, update cache
   - If not found → `simplify_service.create_simplify(...)` — insert DB, write cache
6. `blog_tag_service.list_tag_ids_by_blog_ids([blog_id])` → tag_ids
7. `tag_service.list_tags_by_ids(tag_ids)` → tag names
8. `blog_prerequisite_service.list_prerequisite_ids_by_blog_ids([blog_id])` → prerequisite_ids
9. `prerequisite_service.list_prerequisites_by_ids(prerequisite_ids)` → topic names
10. Return response

Edge cases:
- No JWT → reject
- `content_tier` is `limited` or `partial` → `403`
- RSS feed unavailable → propagate error

---

## `prerequisites/` Handler Design

### `PrerequisiteHandler`

**Constructor dependencies:**
- `prerequisite_service: PrerequisiteService`

---

#### `get_prerequisite(topic_name: str, request: Request) -> PrerequisiteDetail`
Happy path:
1. `decode_jwt_token(request)` — reject if no valid JWT
2. `prerequisite_service.get_prerequisite_by_topic_name(topic_name)` — cache → DB
3. If `content` is None or `check_refresh_due(updated_at)` (from `utils.py`) is stale:
   - `call_llm(prompt)` with prompt from `prompts/prerequisites.py` — returns dict `{"definition": "...", "why_it_matters": "...", "example": "...", "deep_dive": "..."}`
   - `prerequisite_service.update_prerequisite(topic_name, content)` — update DB, update cache
4. Assemble `Primer` from `content` dict — map `definition`, `why_it_matters`, `example` keys into `Primer` object
5. Return `PrerequisiteDetail(topic_name, primer, deep_dive, updated_at)`

**Note:** The row always exists by the time this handler is called — it was created at ingest with topic name + embedding. `content` is NULL until first user click — treated as "never generated" and triggers LLM call unconditionally.

Edge cases:
- No JWT → reject
- LLM fails → propagate error

---

## `ingest/` Handler Design

### `IngestHandler`

**Constructor dependencies:**
- `blog_source_service: BlogSourceService`
- `blog_service: BlogService`
- `tag_service: TagService`
- `blog_tag_service: BlogTagService`
- `prerequisite_service: PrerequisiteService`
- `blog_prerequisite_service: BlogPrerequisiteService`
- `rss_client: RSSClient`
- `embedder: Embedder`

---

#### `trigger_job() -> None`
Happy path:
1. `blog_source_service.list_all_sources()` — fetch all RSS sources (each source has `id`, `source`, `rss_feed_link`)
2. For each source:
   a. `blog_service.get_last_blog_by_source_id(source.id)` — get last known guid
   b. `rss_client.get_feed(source.rss_feed_link)` — fetch RSS feed items using `rss_feed_link` from the source object
   c. Reverse feed list (oldest-first insertion order)
   d. For each article (stop when guid matches last known):
      - `_fetch_thumbnail(link)` — scrape og:image, null on failure
      - `blog_service.insert_blog(...)` — insert blog row
      - `rss_client.get_content(feed_url, guid)` — extract article text from RSS feed item (no scraping)
      - `call_llm(prompt + content)` with prompt from `prompts/ingest.py` — returns tags, prerequisites
      - For each tag: `_process_tag(blog_id, tag_name)`
      - For each prerequisite: `_process_prerequisite(blog_id, topic_name)`

**Private helpers:**
- `_fetch_thumbnail(link)` — scrapes og:image, returns url or None
- `_process_tag(blog_id, tag_name)` — normalize `tag_name` (lowercase, strip, collapse hyphens/underscores/spaces to `-`) → `self.embedder.embed(normalized)` → `tag_service.find_similar_tag(embedding, threshold)` → returns `tuple[Tag | None, float | None]` (match, score). Open a `tag.normalize` OTel span using `tracer = trace.get_tracer("enggsystemfeed.ingest")` defined at module level. Record span attributes: `tag.candidate` (raw LLM output), `tag.normalized`, `tag.similarity_score` (if score not None). If match is not None → `tag.action = "merge"`, record `tag.canonical = match.name`, use existing `tag_id`, discard new embedding. If match is None → `tag.action = "insert"`, `tag_service.create_tag(normalized, embedding)` — stores name + embedding together, use new `tag_id`. Then `blog_tag_service.create_blog_tag(blog_id, tag_id)`.
- `_process_prerequisite(blog_id, topic_name)` — identical pattern. Normalize `topic_name` → embed → `prerequisite_service.find_similar_prerequisite(embedding, threshold)` → `tuple[Prerequisite | None, float | None]`. Open a `prerequisite.normalize` OTel span. Record: `prerequisite.candidate`, `prerequisite.normalized`, `prerequisite.similarity_score` (if not None), `prerequisite.action` (merge/insert), `prerequisite.canonical` (on merge). Insert or merge accordingly. Then `blog_prerequisite_service.create_blog_prerequisite(blog_id, prerequisite_id)`.

Edge cases:
- og:image scraping fails → insert blog with `thumbnail = None`
- LLM call fails → log error, skip article
- RSS feed unavailable → log error, skip source
