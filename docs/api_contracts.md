# API Contracts: Engineering Blog Aggregator

## Base Response Schema (`schemas.py`)

All API responses use a shared envelope defined in `schemas.py` at project root:

```python
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class ErrorDetail(BaseModel):
    code: int
    message: str

class APIResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None
    error: ErrorDetail | None
```

**Success:**
```json
{ "success": true, "data": { ... }, "error": null }
```

**Error:**
```json
{ "success": false, "data": null, "error": { "code": 404, "message": "Blog not found" } }
```

---

## Routes

### `GET /`
- Returns HTML shell (no blog data)
- Blog data is loaded via AJAX call to `/api/v1/blogs` on page load

---

## Auth Endpoints

### `GET /auth/initiate`
- Generates state token, stores it in the `oauth_state` HttpOnly cookie
- Returns the Google OAuth consent screen URL in the JSON response body — does **not** issue an HTTP redirect itself. The frontend is responsible for navigating to the returned `auth_url`.

**Response:** `APIResponse[dict]`
```json
{ "success": true, "data": { "auth_url": "https://accounts.google.com/o/oauth2/..." }, "error": null }
```

---

### `GET /auth/callback`
- Called by Google after user authenticates

**Query Params:**
| Param | Type | Description |
|-------|------|-------------|
| state | string | State token to verify against cookie |
| code | string | Authorization code from Google |

- Verifies state token — rejects if mismatch (redirects to `/?error=auth_failed`)
- Deletes state token after verification
- Exchanges `code` for Google ID token
- Checks `user` table by `google_auth_id` — inserts only if not already present
- Issues JWT with `user_id`, stored in HttpOnly cookie
- **Note:** There is no email allowlist — any Google account that completes OAuth is signed in (`allowed_users` table was dropped)

---

### `GET /auth/me`
- **Role:** USER
- Requires JWT cookie
- Reads `user_id` from JWT, fetches user data from `user` table
- Used by frontend to populate navbar on page load

**Schema** (`auth/schemas.py`):
```python
class UserDetail(BaseModel):
    user_id: uuid.UUID
    name: str
    profile_url: str
```

**Response:** `APIResponse[UserDetail]`
```json
{
  "success": true,
  "data": {
    "user_id": "uuid",
    "name": "John Doe",
    "profile_url": "https://..."
  },
  "error": null
}
```

---

### `POST /auth/logout`
- Clears JWT HttpOnly cookie
- User is signed out

---

## API Endpoints

### `GET /api/v1/blogs`
- **Role:** GUEST, USER
- Returns paginated list of blogs as JSON
- All query params are optional
- JWT cookie is optional — signed-in users get tags populated, guests get empty `tags` array

**Query Params:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| source | string | all | Comma-separated company names — multi-select (e.g. `Cloudflare,GitHub`). Parsed server-side into a list; unknown names are dropped and, if none resolve, treated as "no filter" |
| page | int | 1 | Page number |
| count | int | 20 | Page size |
| tag | string | none | Comma-separated tag names — multi-select (e.g. `kafka,scaling`). Unknown names are dropped; if none resolve, returns an empty result (`total=0`) |

**Schemas** (`blog/schemas.py`):
```python
class ContentTier(str, Enum):
    LIMITED = "LIMITED"
    PARTIAL = "PARTIAL"
    FULL = "FULL"

class BlogItem(BaseModel):
    created_at: datetime
    link: str
    title: str
    thumbnail: str | None
    word_count: int
    published_at: datetime | None
    blog_source_id: uuid.UUID
    source: str
    tags: list[str]
    prerequisites: list[str]
    content_tier: ContentTier

class PaginatedBlogs(BaseModel):
    total: int
    page: int
    count: int
    total_pages: int
    blogs: dict[str, BlogItem]
```

**Response:** `APIResponse[PaginatedBlogs]`
```json
{
  "success": true,
  "data": {
    "total": 100,
    "page": 1,
    "count": 20,
    "total_pages": 5,
    "blogs": {
      "<blog_id>": {
        "created_at": "2024-01-01T00:00:00",
        "link": "https://...",
        "title": "...",
        "thumbnail": "https://...",
        "word_count": 500,
        "published_at": "2024-01-01T00:00:00",
        "blog_source_id": "uuid",
        "source": "Cloudflare",
        "tags": ["kafka", "scaling"],
        "prerequisites": ["Anycast Routing", "BGP"],
        "content_tier": "FULL"
      }
    }
  },
  "error": null
}
```

- `tags` is populated for signed-in users, empty array `[]` for guests
- `prerequisites` is an array of topic name strings — populated for signed-in users (Partial + Full tier), empty array `[]` for guests and Limited tier
- `content_tier` is computed from `word_count` at the handler level — not stored in DB (`LIMITED` < 150 words, `PARTIAL` 150–300, `FULL` 300+)

---

### `GET /api/v1/sources`
- **Role:** GUEST, USER
- Returns list of all blog sources for the company filter dropdown

**Schema** (`blog/schemas.py`):
```python
class BlogSource(BaseModel):
    id: uuid.UUID
    source: str
```

**Response:** `APIResponse[list[BlogSource]]`
```json
{
  "success": true,
  "data": [
    { "id": "uuid", "source": "Cloudflare" },
    { "id": "uuid", "source": "GitHub" }
  ],
  "error": null
}
```

---

### `GET /api/v1/tags`
- **Role:** GUEST, USER
- Returns every tag with its usage count (number of blogs tagged with it), ordered by count descending — used to populate the topic filter pill row

**Schema** (`blog/schemas.py`):
```python
class TagWithCount(BaseModel):
    tag: str
    count: int
```

**Response:** `APIResponse[list[TagWithCount]]`
```json
{
  "success": true,
  "data": [
    { "tag": "kafka", "count": 14 },
    { "tag": "scaling", "count": 9 }
  ],
  "error": null
}
```

---

### `GET /api/v1/blogs/{blog_id}/summary`
- **Role:** USER
- Requires JWT cookie
- Returns AI generated summary for the blog
- Returns `403` if `content_tier` is `LIMITED`

**Schemas** (`summary/schemas.py`):
```python
class SummaryContent(BaseModel):
    short_summary: str
    key_points: list[str]
    updated_at: datetime

class SummaryDetail(BaseModel):
    blog: BlogItem
    summary: SummaryContent
```

**Response:** `APIResponse[SummaryDetail]`
```json
{
  "success": true,
  "data": {
    "blog": {
      "created_at": "2024-01-01T00:00:00",
      "link": "https://...",
      "title": "...",
      "thumbnail": "https://...",
      "word_count": 500,
      "published_at": "2024-01-01T00:00:00",
      "blog_source_id": "uuid",
      "source": "Cloudflare",
      "tags": ["kafka", "scaling"],
      "prerequisites": ["Anycast Routing", "BGP"],
      "content_tier": "FULL"
    },
    "summary": {
      "short_summary": "...",
      "key_points": ["...", "..."],
      "updated_at": "2024-01-01T00:00:00"
    }
  },
  "error": null
}
```

---

### `GET /api/v1/blogs/{blog_id}/simplify`
- **Role:** USER
- Requires JWT cookie
- Returns ELI5 explanation for the blog
- Returns `403` if `content_tier` is `LIMITED` or `PARTIAL`

**Schemas** (`simplify/schemas.py`):
```python
class SimplifyContent(BaseModel):
    content: str
    updated_at: datetime

class SimplifyDetail(BaseModel):
    blog: BlogItem
    simplify: SimplifyContent
```

**Response:** `APIResponse[SimplifyDetail]`
```json
{
  "success": true,
  "data": {
    "blog": {
      "created_at": "2024-01-01T00:00:00",
      "link": "https://...",
      "title": "...",
      "thumbnail": "https://...",
      "word_count": 500,
      "published_at": "2024-01-01T00:00:00",
      "blog_source_id": "uuid",
      "source": "Cloudflare",
      "tags": ["kafka", "scaling"],
      "prerequisites": ["Anycast Routing", "BGP"],
      "content_tier": "FULL"
    },
    "simplify": {
      "content": "...",
      "updated_at": "2024-01-01T00:00:00"
    }
  },
  "error": null
}
```

---

### `POST /api/v1/feedback`
- **Role:** USER
- Requires JWT cookie
- Submits feedback for a blog — one request per type
- Only inserted if `content` is non-empty after stripping whitespace
- Rate limited: 5 submissions per user per day — returns 429 if exceeded
- Validates `content` length server-side: min 10 chars, max 500 chars

**Request body** (`feedback/schemas.py`):
```python
class FeedbackType(str, Enum):
    TAG = "tag"
    PREREQUISITE = "prerequisite"
    SUMMARY = "summary"
    SIMPLIFY = "simplify"

class FeedbackRequest(BaseModel):
    blog_id: uuid.UUID
    type: FeedbackType
    content: str
```

**Response (success):** `APIResponse[None]`
```json
{ "success": true, "data": null, "error": null }
```

**Response (rate limited):**
```json
{ "success": false, "data": null, "error": { "code": 429, "message": "You've reached the feedback limit for today. Try again tomorrow." } }
```

---

### `POST /api/v1/ingest`
- **Role:** Internal — triggered by GitHub Actions cron (daily at 6 AM UTC)
- Not listed in Swagger UI (`include_in_schema=False`)
- Authenticated via `x-ingest-secret` header — validated against `INGEST_SECRET` env var using `secrets.compare_digest`
- Returns `401` if header is missing or does not match

**Headers:**
| Header | Description |
|--------|-------------|
| x-ingest-secret | Shared secret matching `INGEST_SECRET` env var |

**Response (success):** `APIResponse[None]`
```json
{ "success": true, "data": null, "error": null }
```

**Response (unauthorized):**
```json
{ "success": false, "data": null, "error": { "code": 401, "message": "Unauthorized" } }
```

---

### `GET /api/v1/prerequisites/{topic_name}`
- **Role:** USER
- Requires JWT cookie
- Returns on-demand explanation for a prerequisite topic — primer + deep dive
- Lookup order: cache → DB → LLM
- **Note:** `primer` is assembled by the handler from the `content` jsonb column — parsed dict keys `definition`, `why_it_matters`, `example` are mapped into a nested `Primer` object
- **Note:** Response is intentionally minimal — this endpoint is called from a modal when the user clicks a prerequisite chip. Blog context (title, tags, etc.) is already present on the page.

**Schemas** (`prerequisites/schemas.py`):
```python
class Primer(BaseModel):
    definition: str
    why_it_matters: str
    example: str

class PrerequisiteDetail(BaseModel):
    topic_name: str
    primer: Primer
    deep_dive: str
    updated_at: datetime
```

**Response:** `APIResponse[PrerequisiteDetail]`
```json
{
  "success": true,
  "data": {
    "topic_name": "Anycast Routing",
    "primer": {
      "definition": "...",
      "why_it_matters": "...",
      "example": "..."
    },
    "deep_dive": "...",
    "updated_at": "2024-01-01T00:00:00"
  },
  "error": null
}
```
