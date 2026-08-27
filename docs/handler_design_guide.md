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
- `generate_jwt_token(user_id: uuid.UUID) -> str`
- `decode_jwt_token(token: str) -> dict` — lives in `auth/utils.py`; imported from there by all modules that need to verify JWT. Raises `UnauthorizedError` if invalid or expired.
- `is_authenticated(token: str | None) -> bool` — returns `True` if the token is present and valid, `False` otherwise (swallows `UnauthorizedError`). Used by `blog/controller.py` to compute `is_signed_in` without raising on guest requests.

**Convention:** Controllers extract the JWT cookie value themselves (`request.cookies.get("access_token")`) and pass a plain `token: str | None` into the handler. Handlers never take `Request`/`Response` — they call `decode_jwt_token(token)` on the plain string.

---

### `AuthHandler`

**Constructor dependencies:**
- `auth_client: AuthClient`
- `user_service: UserService`

**Note:** There is no allowlist gate — the `allowed_users` table was dropped (`alembic/versions/9da7f10dbd4f_drop_allowed_users_table.py`). Any Google account that completes OAuth successfully is signed in.

---

#### `initiate() -> tuple[str, str]`
Returns `(state, auth_url)` — no params, does not touch cookies itself.
Happy path:
1. Generate a state token (`secrets.token_urlsafe(32)`)
2. `auth_client.get_auth_url(state)` — build Google OAuth URL
3. Return `(state, auth_url)` — the **controller** sets the `oauth_state` HttpOnly cookie from `state` and returns `auth_url` in the JSON response body (the frontend does the redirect — this endpoint does not itself 302).

---

#### `callback(code: str, state: str, stored_state: str | None) -> str`
Returns the JWT token string — the **controller** sets it as the `access_token` HttpOnly cookie and issues the redirect.
Happy path:
1. Compare `stored_state` (read from the `oauth_state` cookie by the controller) against `state` (query param) — raise `AuthError` on mismatch
2. `auth_client.exchange_code(code)` — call Google token endpoint, get ID token
3. `auth_client.verify_id_token(id_token)` — verify audience + `email_verified`, extract email + `google_auth_id` + `name` + `picture`
4. `user_service.get_user_by_auth_id(google_auth_id)` — check if returning user
5. If None → `user_service.create_user(...)` — insert new row
6. `generate_jwt_token(user_id)` — return the token string

Edge cases:
- State mismatch → `AuthError` → controller redirects to `/?error=auth_failed`

---

#### `me(token: str | None) -> UserDetail`
Happy path:
1. If `token` is falsy → raise `UnauthorizedError`
2. `decode_jwt_token(token)` — extract `user_id` from the payload
3. `user_service.get_user_by_id(user_id)` — fetch name, profile_url; raise `NotFoundError` if missing
4. Return `UserDetail`

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

#### `get_blogs(sources: list[str] | None, tags: list[str] | None, page: int, count: int, is_signed_in: bool) -> PaginatedBlogs`
`sources`/`tags` are multi-select — the **controller** parses comma-separated `source`/`tag` query params into these lists and resolves `is_signed_in` via `is_authenticated(request.cookies.get("access_token"))` before calling the handler. The handler itself takes no `Request`.

Happy path:
1. For each name in `sources` → `blog_source_service.get_source_by_name(name)` → collect resolved `source_id`s (skip unknown names)
2. For each name in `tags` → `tag_service.get_tag_by_name(name)` → collect resolved `tag_id`s; if `tags` was non-empty but nothing resolved, short-circuit and return an empty `PaginatedBlogs`
3. `blog_service.list_blogs(source_ids, tag_ids, None, page, count)` / `count_blogs(...)` — DAO uses `IN` clauses for multi-select
4. Compute `content_tier` for each blog from `word_count` (`LIMITED` < 150, `PARTIAL` 150–300, `FULL` 300+)
5. If `is_signed_in` and there are blogs on the page:
   - `blog_tag_service.list_tag_ids_by_blog_ids(blog_ids)` → tag_ids per blog
   - `tag_service.list_tags_by_ids(tag_ids)` → tag names
   - Filter to non-`LIMITED` tier blog_ids only → `eligible_blog_ids`
   - `blog_prerequisite_service.list_prerequisite_ids_by_blog_ids(eligible_blog_ids)` → prerequisite_ids per blog
   - `prerequisite_service.list_prerequisites_by_ids(prerequisite_ids)` → prerequisite rows (topic names + ids)
   - Attach tags and prerequisites to each blog (both stay empty arrays if not signed in, or for `LIMITED` tier)
6. Return enriched list. Server-side pagination applies via `page` and `count`.

Edge cases:
- Guest user (`is_signed_in=False`) → tags and prerequisites are empty arrays
- `tags` param present but none resolve to a known tag → empty result (`total=0`)
- `sources` param present but none resolve → treated as "no source filter" (falls back to `None`), not an empty result

---

#### `get_sources() -> list[BlogSource]`
Happy path:
1. `blog_source_service.list_all_sources()` → return list

---

#### `get_tags() -> list[TagWithCount]`
Happy path:
1. `tag_service.list_all_tags_with_counts()` → list of `(Tag, count)` tuples, ordered by count descending
2. Map to `TagWithCount(tag=tag.tag, count=count)` per row

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

#### `get_summary(blog_id: str, token: str | None) -> SummaryDetail`
**Invariant:** A `summary` row is never created at ingest time. The `summary` table is populated only on first user request. Do not add any code path that assumes a `summary` row exists for a blog that has been ingested.

Happy path:
1. If `token` is falsy → raise `UnauthorizedError`; else `decode_jwt_token(token)`
2. `blog_service.get_blog_by_id(uuid.UUID(blog_id))` — fetch title, link, thumbnail, word_count, blog_source_id, guid; raise `NotFoundError` if missing
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

#### `get_simplify(blog_id: str, token: str | None) -> SimplifyDetail`
**Invariant:** A `simplify` row is never created at ingest time. The `simplify` table is populated only on first user request. Do not add any code path that assumes a `simplify` row exists for a blog that has been ingested.
Happy path:
1. If `token` is falsy → raise `UnauthorizedError`; else `decode_jwt_token(token)`
2. `blog_service.get_blog_by_id(uuid.UUID(blog_id))` — fetch title, link, thumbnail, word_count, blog_source_id, guid; raise `NotFoundError` if missing
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

#### `get_prerequisite(topic_name: str, token: str | None) -> PrerequisiteDetail`
Happy path:
1. If `token` is falsy → raise `UnauthorizedError`; else `decode_jwt_token(token)`
2. `prerequisite_service.get_prerequisite_by_topic_name(topic_name)` — cache → DB; raise `NotFoundError` if the row itself doesn't exist
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
3. After all sources are processed (success or failure): `_check_monthly_budget()`

**Private helpers:**
- `_fetch_thumbnail(link)` — scrapes og:image, returns url or None
- `_check_monthly_budget()` — sums this calendar month's `llm_usage.cost_usd` via `llm_usage_service.get_monthly_costs(month_start)`. If total exceeds `settings.LLM_MONTHLY_COST_ALERT_USD` (env `LLM_MONTHLY_COST_ALERT_USD`, default `10.00`), logs a warning and calls `sentry_sdk.capture_message(...)`. Wrapped in its own try/except — a failure here is logged/captured but never aborts the ingest job. Runs once per ingest job (daily cadence via GitHub Actions cron), not a real-time spend guard — added after an incident where LLM credits ran out mid-month with no visibility. Does **not** cover spend from one-off scripts (`backfill_*.py`) that bypass `LLMUsageService.create_llm_usage`.
- `_process_tag(blog_id, tag_name)` — normalize `tag_name` (lowercase, strip, collapse hyphens/underscores/spaces to `-`) → `self.embedder.embed(normalized)` → `tag_service.find_similar_tag(embedding, threshold)` → returns `tuple[Tag | None, float | None]` (match, score). Open a `tag.normalize` OTel span using `tracer = trace.get_tracer("enggsystemfeed.ingest")` defined at module level. Record span attributes: `tag.candidate` (raw LLM output), `tag.normalized`, `tag.similarity_score` (if score not None). If match is not None → `tag.action = "merge"`, record `tag.canonical = match.name`, use existing `tag_id`, discard new embedding. If match is None → `tag.action = "insert"`, `tag_service.create_tag(normalized, embedding)` — stores name + embedding together, use new `tag_id`. Then `blog_tag_service.create_blog_tag(blog_id, tag_id)`.
- `_process_prerequisite(blog_id, topic_name)` — identical pattern. Normalize `topic_name` → embed → `prerequisite_service.find_similar_prerequisite(embedding, threshold)` → `tuple[Prerequisite | None, float | None]`. Open a `prerequisite.normalize` OTel span. Record: `prerequisite.candidate`, `prerequisite.normalized`, `prerequisite.similarity_score` (if not None), `prerequisite.action` (merge/insert), `prerequisite.canonical` (on merge). Insert or merge accordingly. Then `blog_prerequisite_service.create_blog_prerequisite(blog_id, prerequisite_id)`.

Edge cases:
- og:image scraping fails → insert blog with `thumbnail = None`
- LLM call fails → log error, skip article
- RSS feed unavailable → log error, skip source

---

## `feedback/` Handler Design

### `FeedbackHandler`

**Constructor dependencies:**
- `feedback_service: FeedbackService`

---

#### `submit_feedback(blog_id: uuid.UUID, type: FeedbackType, content: str, token: str | None) -> APIResponse`
Happy path:
1. If `token` is falsy → raise `UnauthorizedError`; else `decode_jwt_token(token)`, extract `user_id`
2. Check per-minute rate limit — Redis key `feedback:{user_id}:minute:{YYYYMMDDHHMM}` (TTL 60s), increment and check against `FEEDBACK_RATE_LIMIT_PER_MINUTE` from `constants.py`. If exceeded → raise `RateLimitError` (429)
3. Check per-day rate limit — Redis key `feedback:{user_id}:{YYYYMMDD}`, increment and check against `FEEDBACK_RATE_LIMIT_PER_DAY` from `constants.py`. If exceeded → raise `RateLimitError` (429)
4. Strip `content` — if empty after stripping → return `APIResponse(success=True, ...)` without inserting
5. Validate `content` length — min 10 chars, max 500 chars → raise `ValidationError` if out of range
6. `feedback_service.create_or_update(user_id, blog_id, type, content)` — service internally looks up the existing row via `get_feedback_by_user_blog_type` and calls `update_feedback` (passing the row object) if found, else `create_feedback`
7. Return `APIResponse(success=True, data=None, error=None)`

Edge cases:
- No JWT → reject with 401
- Rate limit exceeded → 429
- Content empty after strip → no insert, return success
- Content too short (< 10) or too long (> 500) → 422
- Duplicate submission (same user, blog, type) → update existing row
