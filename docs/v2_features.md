# V2 Features

Features deferred from v1 — to be revisited after launch.

---

## Evals

Evaluate LLM output quality across summary, simplify, tags, and prerequisites.

- **Summary** — accuracy, length, hallucination check
- **Tags** — relevance to article, normalization correctness
- **Prerequisites** — are extracted topics actually required to understand the article?
- **Simplify** — is the ELI5 actually simple and correct?

**Approach:** Sample articles, run prompts, score outputs manually or with LLM-as-judge. Pair with prompt versioning to measure quality delta between prompt changes.

**Why deferred:** Adds significant overhead before shipping. Better to observe real v1 outputs first, identify weak spots, then target evals at those.

---

## Prompt Versioning

Track which prompt version generated each stored output (summary, simplify, prerequisites).

- Store `prompt_version` alongside generated content in DB
- Enables rollback and A/B testing of prompt changes
- Pairs with evals to measure impact of prompt changes

**Why deferred:** Git handles prompt change history. 7-day refresh naturally propagates new prompts. Not needed until prompt experimentation begins.

---

## Model Versioning

Track which model version (e.g., `claude-sonnet-4-6`) generated each stored output (summary, simplify, prerequisites).

- Store `model_version` alongside generated content in DB
- When model is upgraded, existing rows retain their version — 7-day refresh gradually migrates them to the new model
- Pairs with evals to compare output quality across model versions

**Why deferred:** Model upgrades are infrequent in v1. 7-day refresh handles migration naturally. Add when model experimentation begins.

---

## Prerequisite Content Depth

Revisit primer and deep dive structure and length after observing real user interaction in v1.


---

## Agentic Tagging Pipeline (v2)

Replace single-prompt tag and prerequisite extraction with a multi-step agentic flow.

- **Self-critique loop** — separate agent steps: one generates candidates, a second critiques and selects with explicit reasoning. Reduces overlapping or redundant tags.
- **Vocabulary-anchored tagging** — agent gets a `lookup_existing_tags` tool that checks candidates against the seed tag vocabulary. Anchors to known-good tags where they fit, only coins new ones when nothing matches. Keeps the tag space consistent across articles over time.

**Why deferred:** Single-prompt generate-then-select works well enough for v1. Agentic flow adds latency and complexity — better to identify specific failure modes from real v1 outputs first.

---

## Agentic Content Fetch (v3)

Agent fetches the full article URL and extracts clean text before tagging, summarizing, or generating prerequisites.

- RSS content is often truncated or HTML-heavy — full article fetch produces significantly better LLM outputs
- Particularly impactful for prerequisites, where depth and nuance matter

**Why deferred:** Adds scraping complexity and fragility (site layout changes, bot blocking). Evaluate whether RSS content quality is a real bottleneck in v1 before investing here.

---

## Agentic Prerequisite Depth (v3)

Agent recursively determines how deeply a prerequisite needs to be understood to follow the article.

- e.g., "TCP" as a prerequisite — does the reader need to understand it deeply, or just know it exists?
- Pairs with Prerequisite Content Depth feature above

**Why deferred:** Depends on observing real user interaction patterns with prerequisites in v1.

---

## Skip Paywall-Truncated Substack Posts (v3)

Some Substack sources (e.g. Pragmatic Engineer's "The Pulse" roundups) ship RSS items cut off mid-article at the paywall, ending in a trailing `Read more` CTA link back to the post's own URL. Existing word-count-based `ContentTier` gating (`CONTENT_TIER_LIMITED_MAX_WORDS`/`CONTENT_TIER_PARTIAL_MAX_WORDS` in `constants.py`) doesn't reliably catch these — a truncated post can still have enough preview words to score `PARTIAL` or even `FULL`, so it still runs through LLM calls (summary/tags) against incomplete content.

- Detection: Substack-specific paywall-truncation marker (trailing "Read more" link back to the post's own URL) — not a generic cross-platform teaser heuristic.
- Action on detection: skip ingesting the row entirely (not stored, not shown in the feed) — different from the existing `LIMITED` tier behavior, where thin articles are still inserted and shown but skip LLM calls.
- Likely touches `rss_client.py` (detection) and `ingest/handler.py::_process_article` (skip-insert).

**Why deferred:** Only currently relevant to Pragmatic Engineer's "Pulse" posts. Related to Agentic Content Fetch above — worth revisiting together.

---

## Independent Publisher/Author Filter Row (v3)

Third filter row, alongside the existing Company and Topic rows, for sources run by an individual rather than a company (e.g. Pragmatic Engineer, All Things Distributed, Engineer's Codex).

- Add `blog_source.source_type` column (`COMPANY` / `INDEPENDENT` enum) — Alembic migration, backfilled for existing rows.
- `blog/models.py::BlogSource`, `blog/schemas.py::BlogSource` (+ new `SourceType` enum), `blog/dao.py`/`blog/service.py` (`IBlogSourceDAO.list_all`/`list_all_sources` need to expose the field, or a new filtered lookup), `blog/handler.py::get_sources` — expose `source_type` per source.
- Frontend (`templates/index.html`): third sticky filter pill row + modal, split from the current single Company row.
- `eval/seed_blog_source.sql`: add `source_type` per row.
- Docs to update once implemented: `docs/schema.md`, `docs/dao_and_service_class_design.md`, `docs/api_contracts.md` (`GET /api/v1/sources`), `docs/ux_decisions.md`.

**Why deferred:** Only 3 of 19 current sources are independent — user confirmed the schema approach (source_type column) but deferred implementation.

---

## Ops: Purge Fly.io and Google Sources

Both dropped from `eval/seed_blog_source.sql` already. Full purge still pending on actual DB rows (local + production):

- **Fly.io** — `rss_feed_link` (`fly.io/changelog.xml`) 404s, feed is dead. Confirmed **not present** in local `blog_source` (seed insert likely never ran there) — production not yet checked.
- **Google** (feedburner, `feeds.feedburner.com/GDBcode`) — feed has no date field on any item at all (no `pubDate`/`updated`/`dc:date`), despite `Blog.published_at` being `NOT NULL`; unclear how/whether ingest has been succeeding for this source. Confirmed present in local `blog_source` with **40** already-ingested `Blog` rows — production not yet checked.

**To do when picked back up:**
1. SSH into production, check `blog_source` for both names (Fly.io may or may not exist there — check independently of local).
2. Full purge, per row that exists: delete `blog_tag`, `blog_prerequisite`, `llm_usage`, `summary`, `simplify` rows for every `Blog` under that source, then the `Blog` rows themselves, then the `blog_source` row. Do NOT delete shared `tag`/`prerequisite` vocabulary rows — only the blog-level links.
3. Run on local first, verify, then production.

---

## Candidate Source: Engineer's Codex

`https://read.engineerscodex.com/feed` — evaluated 2026-08-27: full content, no paywall, good quality (see "Skip Paywall-Truncated Substack Posts" above for the Substack-family evaluation notes). Independent publisher, not a company.

**Not seeded** — last post was 2026-05-07 (111 days stale as of this check, by far the most stale of any evaluated source). Revisit if the blog resumes posting.
