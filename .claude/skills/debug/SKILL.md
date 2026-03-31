---
name: debug
description: Diagnose and fix issues in the enggsystemfeed stack — Docker, FastAPI, PostgreSQL, Redis, Alembic, and Alpine.js.
---

Help the user debug the issue described in $ARGUMENTS.
If $ARGUMENTS is empty, ask the user to describe the symptom (error message, unexpected behaviour, failing endpoint, etc.).

Read any relevant source files before suggesting a fix. Do not suggest changes to code you haven't read.

---

## Diagnosis approach

1. **Identify the layer** — is the issue in Docker/infra, FastAPI startup, a specific endpoint, the database, Redis, ingest, or the frontend?
2. **Gather evidence** — ask for logs, error messages, or HTTP responses if not already provided.
3. **Pinpoint the cause** — trace through the layer stack (Controller → Handler → Service → DAO) to find where it breaks.
4. **Suggest a fix** — minimal, targeted. Do not refactor surrounding code.
5. **Verify** — tell the user how to confirm the fix worked.

---

## Common issues and first steps

### App won't start / import errors
```bash
docker compose logs app
```
- `ModuleNotFoundError` → missing package in `requirements.txt`, or wrong import path
- `ValidationError` on startup → env var missing or wrong type in `config.py` — check `.env.local`
- `OperationalError` connecting to DB → PostgreSQL container not ready, or `DATABASE_URL` wrong

### Database / migration issues
```bash
docker compose exec app alembic upgrade head    # run pending migrations
docker compose exec app alembic current         # check which revision is applied
```
- `relation does not exist` → migration not run, or run against wrong DB
- `column does not exist` → schema out of sync — check `docs/schema.md` vs actual table
- `pgvector extension not found` → `CREATE EXTENSION IF NOT EXISTS vector` not in migration

### API returns unexpected response
- Check `docker compose logs app` for tracebacks
- Verify endpoint path and params against `docs/api_contracts.md`
- Check controller exception handling — all exceptions should be caught and returned as `APIResponse(success=False, ...)`
- Check HTTP status code mapping in `docs/tech_decisions.md` (error handling section)

### Caching issues
- Open RedisInsight at `http://localhost:5540` → browse keys
- `use_cache=False` should only be passed by handlers after a staleness check — verify controller is not passing it
- Cache key collision: check DAO method cache key format

### Ingest not working
```bash
docker compose logs app | grep -i ingest
```
- LLM call failing → check `ANTHROPIC_API_KEY` in `.env.local`, check timeout in `config.py`
- Embedding call failing → check `OPENAI_API_KEY`, confirm `SearchUnreachableError` is raised (not `LLMUnreachableError`)
- Duplicate blog rows → `blog.id` is `guid` (PK) — duplicate inserts are silently ignored by PK constraint, not an error
- Tags not appearing → `INGEST_PROMPT` is still `None` (stub) — prompt must be written before tags/prerequisites are extracted

### Frontend issues
- AJAX call failing → open browser devtools → Network tab → check request URL and response body
- URL not updating → verify `history.pushState` is called in the Alpine.js handler
- Modal not opening/closing → check Alpine.js `x-show` binding and `$dispatch` calls
- API response shape mismatch → compare response fields against `docs/api_contracts.md`
- Alpine.js data not reactive → ensure the property is declared in `x-data` before being set

### Auth issues
- `401` on `/auth/me` → JWT cookie missing or expired (2hr expiry) — sign in again
- OAuth callback fails → check `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` in `.env.local` match Google Cloud Console settings
- User rejected despite valid Google account → email not in `allowed_users` table — add it via pgadmin

---

## Architecture reminders for debugging

- Controllers catch all exceptions and return `APIResponse` — a 500 from FastAPI means the exception escaped the controller
- Handlers raise business logic exceptions — if a handler is raising `DatabaseError`, the DAO is not wrapping it correctly
- DAOs catch SQLAlchemy exceptions and re-raise as `DatabaseError` — raw SQLAlchemy errors should never reach the controller
- `content_tier` is computed in the handler, never stored in DB — if it's wrong, check `constants.py` thresholds and handler logic
- Summary/simplify rows are never created at ingest — only on first user request. A missing row is expected until the endpoint is hit.
