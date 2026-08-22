# Decided Next Steps

Decisions reached in discussion on 2026-08-21, not yet implemented. Context/reasoning for each is in `docs/problems_solved.md` ("Summary/Simplify/Prerequisites failing on server") where relevant — this file is the implementation checklist.

---

## 1. Eager summary/simplify generation at ingest

**Why:** `summary/handler.py` and `simplify/handler.py` currently fetch article content on demand via `RSSClient.get_content(feed_url, guid)` on first user request. Most RSS feeds only carry a rolling window of recent items (Cloudflare's holds ~20, ~2 weeks) — once an article ages out, `get_content` permanently fails with a 502. Generating eagerly at ingest, while the article is still guaranteed to be in the feed, removes this failure mode entirely. It also removes the latency hit of a synchronous LLM call on a user's first request.

**What:**
- In `ingest/handler.py:_process_article`, after the existing tags/prerequisites LLM call, also generate summary and simplify — reuse the same `content` variable already fetched via `get_content()` for `INGEST_PROMPT`, no extra RSS fetch needed.
- Tier-gate the same way the read-side handlers already do: summary for FULL + PARTIAL tier, simplify for FULL tier only (skip for LIMITED, same as the existing `word_count < CONTENT_TIER_LIMITED_MAX_WORDS` skip).
- `ingest/handler.py`'s constructor needs `SummaryService` and `SimplifyService` injected (same pattern as the existing `PrerequisiteService`/`BlogPrerequisiteService` injection).
- `summary/handler.py:get_summary` and `simplify/handler.py:get_simplify` become pure reads once refresh logic is removed (see #2) — no LLM call, no RSS dependency, ever, on the read path.
- Raw article content is still **not stored** anywhere — only the LLM output (`summary`/`simplify` DB rows) persists, same as today. This preserves the existing "no content storage, no scraping" decision.

**Cost trade-off (already discussed and accepted):** every non-limited-tier article now costs 2-3 LLM calls at ingest (tags/prerequisites + summary + simplify) regardless of whether any user ever requests it, vs. today's model of paying only per actual request. Net cost is likely a wash or better for anything read more than once, given the 7-day refresh removal below.

---

## 2. Drop the 7-day refresh cycle entirely

**Why:** The refresh cycle (`check_refresh_due` comparing `updated_at` against `REFRESH_INTERVAL_DAYS`) only ever existed to opportunistically pick up future prompt/model improvements. Confirmed with the user: prompt/model changes are expected to be rare, and when they do happen, a deliberate manual regeneration is a better fit than an always-on check that runs on every single request — and for summary/simplify specifically, that check was also what re-triggered the exact live-RSS-fetch bug above on every stale read.

**What:**
- Remove the `check_refresh_due` branch from `summary/handler.py`, `simplify/handler.py`, and `prerequisites/handler.py`. All three become generate-once:
  - Summary/simplify: generated once at ingest (see #1), never regenerated automatically.
  - Prerequisites: still generated on-demand at first user click (no content-aging risk — topic-name-keyed LLM call, no RSS dependency), just without the periodic refresh afterward.
- `REFRESH_INTERVAL_DAYS` (`constants.py`/`config.py`) and `check_refresh_due()` (`utils.py`) likely become dead code — confirm nothing else references them before deleting.
- Manual regeneration remains possible via the existing `force_update` flag already present in `SummaryService.get_summary_by_blog_id` / `SimplifyService.get_simplify_by_blog_id` (DAO-level) — no new mechanism needs to be built for the rare future case.

---

## 3. Remove sign-in / auth entirely

**Why:** Google OAuth is currently in "Testing" publishing status in Google Cloud Console, which caps access to a manually-added test-user list — currently just 1 person. There's no in-app allowlist (`auth/handler.py:callback` upserts any user who completes OAuth, no gate in code) — the restriction is entirely a Cloud Console setting. Since the auth requirement also wasn't functioning as cost/rate-limit control (prerequisites/summary/simplify are keyed to ingest-bounded entities — `topic_name`/`blog_id` — not arbitrary user input, so cost exposure was never actually gated by sign-in), there's no reason to keep a login flow that's currently unusable by anyone but one account.

**What:**
- Remove the JWT/auth requirement from `blog/`, `summary/`, `simplify/`, `prerequisites/` handlers — drop the `if not token: raise UnauthorizedError` / `decode_jwt_token(token)` calls.
- Tags, prerequisites, summary, simplify become available to all users — no more Guest vs. Signed-in split.
- Delete the `auth/` module entirely (client, controller, dao, service, handler, utils, schemas) — no dormant/unused code left behind.
- Frontend: remove the sign-in modal/flow, navbar sign-in/avatar UI, and any `x-show` gating tied to auth state on cards/pages.
- `docs/product_decisions.md`: the "User Tiers" section (Guest vs. Signed-in) needs rewriting — there's effectively one tier now.
- `docs/product_decisions.md` Ads section currently places ads on Summary/Simplify pages "signed-in users only (these pages are auth-gated)" — this needs revisiting now that those pages aren't gated.
- Schema: drop the `user` table entirely — nothing references it once `auth/` and `feedback.user_id` (see #4) are both gone.

---

## 4. Feedback becomes anonymous

**Why:** `feedback.user_id` is a hard FK to `user.user_id` and the existing rate limit (`FEEDBACK_RATE_LIMIT_PER_MINUTE`/`_PER_DAY` in `feedback/handler.py`) is keyed by `user_id`. With no auth, there's no `user_id` to attach feedback to or rate-limit by.

**What:**
- Migration: drop `feedback.user_id` FK/column entirely — not replaced with an IP column (see below).
- `feedback/handler.py:submit_feedback`: remove the `token`/`decode_jwt_token` requirement entirely.
- Re-key the existing Redis rate-limit logic (`feedback:{key}:minute:...` / `feedback:{key}:{day}...`) from `user_id` to client IP — same mechanism, same constants, just a different key. IP is only ever used transiently for this Redis key, not persisted anywhere — no `ip_hash` column on the `feedback` row, since nothing calls for storing it beyond the rate-limit check itself.
- Client IP flows from `feedback/controller.py` (extracted from FastAPI's `Request` object — the layer that already does HTTP parsing) down into `feedback/handler.py` as a plain string parameter, same pattern `token` already uses today. Mind proxy headers like `X-Forwarded-For` if the app sits behind a reverse proxy/load balancer in production.
- `docs/product_decisions.md` User Feedback section says "Signed-in users only" and "Rate limit: 5 submissions per user per day" — update to reflect anonymous + per-IP.

---

## 5. Honeypot field for feedback spam

**Why:** Cheap, zero-dependency deterrent against unsophisticated bots, complementary to IP rate limiting (which is the real defense against a deliberate human spammer). No new service, no new package.

**What:**
- Frontend: add a hidden input field to the feedback form (Alpine.js) — hidden via CSS (off-screen or `display:none`, not `type="hidden"`), named something a bot would plausibly auto-fill (e.g. `website`).
- Backend: `feedback/handler.py` checks the field on submit — if non-empty, silently reject (return success without persisting, so the bot doesn't learn the trick worked or failed) rather than raising a visible error.

---

## Docs needing updates once implemented

`CLAUDE.md` (module responsibility table, `summary`/`simplify`/`prerequisites` refresh-logic descriptions), `docs/product_decisions.md` (user tiers, ads placement, feedback section), `docs/tech_decisions.md` (refresh/cache section), `docs/schema.md` (`user`, `feedback` table reasoning, `updated_at` refresh-cycle notes on `summary`/`simplify`/`prerequisite`), `docs/handler_design_guide.md` (Summary/Simplify/Prerequisite handler designs reference the refresh check), `docs/ux_decisions.md` (spinner-on-7-day-refresh UX no longer applies), `docs/v2_features.md` (prompt versioning / model migration deferral rationale leaned on the 7-day refresh as a stopgap — that stopgap is gone, worth a note).

---

## 6. Move daily ingest scheduling from GitHub Actions to AWS EventBridge

**Why:** `docs/deployment-aws.md` confirms the daily ingest cron (`.github/workflows/daily_ingest.yml`, `schedule: cron: '0 6 * * *'`) never actually ran in production — GitHub auto-disables scheduled workflows after 60 days of repo inactivity, and it was never re-enabled. Alternatives considered and ruled out:
- A plain crontab entry on the EC2 box — works, but the user finds Linux cron hard to manage/debug (no built-in logging/run history, silent failures).
- An intentional filler commit every ~59 days to reset GitHub's inactivity clock — mechanically works (any repo activity resets it, not just workflow runs), but just relocates the problem to "remember to act every 59 days, forever, with no reminder system" — still fails silently if forgotten, and can't be self-automated via another scheduled GitHub Action without hitting the same 60-day disable rule.
- A recurring Google Calendar reminder to prompt that filler commit — closes the "forgetting" gap, but still human-in-the-loop.

**Decision:** AWS EventBridge Scheduler. Cost is negligible at this volume (~365 invocations/year, effectively fractions of a cent, likely within free tier) and it doesn't silently disable itself the way GitHub Actions does — has a UI and run history instead.

**What:** EventBridge Scheduler rule on a cron/rate expression, targeting an API destination that calls the ingest endpoint the same way GitHub Actions does today (`POST` to the ingest URL with the `x-ingest-secret` header). Once confirmed working, retire (or leave disabled as a manual-trigger-only fallback via `workflow_dispatch`) the `schedule:` trigger in `daily_ingest.yml`.

**Related, already-flagged issue to check while touching deploy infra:** `.github/workflows/deploy.yml` still SSHes into a DigitalOcean host (`DO_HOST`/`DO_USER`/`DO_SSH_KEY`) that `docs/deployment-aws.md` confirms was deleted after migrating to the current AWS EC2 instance — a push to `production` right now would fail at the deploy step. Worth fixing alongside this, not strictly part of the EventBridge move itself.

---

## 7. Track LLM cost per ingest run

**Why:** Once eager summary/simplify generation lands (#1), every non-limited-tier article costs up to 3 Anthropic calls at ingest (tags/prerequisites, summary, simplify), plus OpenAI embedding calls for tag/prerequisite normalization. Want visibility into per-day cost and article count over time, not just a one-off log line.

**Decision:** persist to a new DB table rather than just logging, with pricing hardcoded (no live pricing API exists), broken out by both `model_name` and `call_purpose` (not blended into one number), and embedding calls are in scope alongside the 3 Anthropic calls. Also want a protected read endpoint to view it (not just querying via pgAdmin).

**Call purposes — not 4 evenly-shaped buckets, 5:** tags and prerequisites are *not* two separate LLM calls — `INGEST_PROMPT` is a single Claude call per article returning both together (`ingest/handler.py:_process_article`). What *does* naturally split is the embedding/normalization step that follows: `_process_tag` embeds each tag candidate and `_process_prerequisite` embeds each prerequisite candidate as separate `embed_text()` calls. So the real taxonomy is:
- `ingest_extraction` — Claude, one combined call per article (tags + prerequisites together)
- `tag_embedding` — OpenAI, one per tag candidate
- `prerequisite_embedding` — OpenAI, one per prerequisite candidate
- `summary` — Claude
- `simplify` — Claude

**Row granularity — confirmed:** one row per `(day, model, call_purpose)` — up to 5 rows per day, one per purpose above. This is the granularity the read endpoint needs to be designed around, so cost can be sliced any way (total for the day, total per purpose across days, total per model, etc.) rather than only ever seeing one blended number.

**What:**
- New table — columns: `run_date`/`created_at`, `model_name`, `call_purpose` (one of the 5 above), `call_count`, `input_tokens`, `output_tokens`, `estimated_cost_usd`. `articles_ingested` gets its own column keyed by `run_date` only — not repeated across that day's 5 purpose rows, since it doesn't vary per purpose.
- Structural note: `ingest/` currently has no `dao.py` or `service.py` of its own — it only writes through other modules' services (`blog_service`, `tag_service`, etc.). This needs a new `ingest/dao.py` + `ingest/service.py` to keep the Controller → Handler → Service → DAO layering, plus a migration, plus updates to `docs/schema.md`, `docs/dao_and_service_class_design.md`, and the folder-structure/module-responsibility sections of `CLAUDE.md` (currently doesn't document `ingest/` as owning a DAO/Service).
- `utils.py:call_llm()` needs to return/capture `message.usage.input_tokens`/`output_tokens` from the Anthropic SDK response instead of discarding it (already available today, no new dependency). `utils.py:embed_text()` needs the equivalent for OpenAI's embedding response usage data.
- `ingest/handler.py:trigger_job()`/`_process_article`/`_process_tag`/`_process_prerequisite` accumulate token totals per purpose across the run, computes `estimated_cost_usd` per purpose from hardcoded pricing constants in `constants.py` (Claude Sonnet rates + OpenAI `text-embedding-3-small` rates), writes the row(s) at the end.
- New **GET** read endpoint in `ingest/controller.py`, protected the same way the existing `POST /api/v1/ingest` trigger is — reuses `INGEST_SECRET` via the same `x-ingest-secret` header + `secrets.compare_digest` check (no new dedicated setting; still an internal-only surface, and `auth/` is being removed per #3 so this can't lean on JWT/session auth anyway). Needs to support both the granular `(day, model, call_purpose)` breakdown and an aggregate/total view — exact query params and response shape to be worked out at implementation time, not prescribed here.
