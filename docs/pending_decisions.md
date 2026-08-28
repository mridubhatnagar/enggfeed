# Pending Decisions

---

## LLM Model Choice — Resolved

**Decision: Claude Sonnet 4.6.** Hardcoded throughout (`utils.py` `call_llm`, `prompts/*.py`) and confirmed via `eval/phase1_generate.py` (see `docs/SETUP.md` → "Run evals first"). GPT-4.1 is not used for generation anywhere in the codebase — OpenAI is used only for `text-embedding-3-small` embeddings, a separate concern.

| | Sonnet 4.6 | GPT-4.1 |
|---|---|---|
| Input | $3.00/Mtok | $2.00/Mtok |
| Output | $15.00/Mtok | $8.00/Mtok |
| Cache read | $0.15/Mtok | $0.50/Mtok |

(Cost table kept for reference — the original tradeoff reasoning is in git history / `docs/tech_decisions.md`.)

---

## Tagging Pipeline — Resolved

- Tags are LLM freeform — normalization via embedding + cosine similarity (threshold: 0.88) at ingest. See `docs/tech_decisions.md` Tags section.
- Prompt is finalized in `prompts/ingest.py` (full text in `docs/prompts.md`), validated via the eval process in `docs/SETUP.md`.
- The "feed RSS `<category>` values to LLM as hints" idea was not adopted — `INGEST_PROMPT` only takes `title` and `content`, no category hints are passed.

---

## Default Feed Ranking for Old-but-Freshly-Fetched Articles — Open

`blog/dao.py::list_blogs()` sorts by `Blog.created_at.desc()` (fixed 2026-08-27 — was previously `published_at.desc()`, which buried freshly-fetched articles with older publish dates deep in the feed). The `created_at` sort fixes that, but introduces the reverse case: an old article (e.g. published in May) that gets fetched today — via a cron gap being caught up, a newly-onboarded source's backlog, or a backfill — ranks at the very top of the feed, ahead of things published more recently. The card still shows the true `published_at`, so it's not deceptive, but it can look wrong (an old post as today's top story).

**Options discussed, not yet decided:**
- Cap the freshness boost by age — an article only sorts by `created_at` if `published_at` is within some window (e.g. 30/60 days); older backlog content sorts by `published_at` instead, so it doesn't jump to the top but also isn't buried.
- Accept as-is — pure `created_at` sort is how most feed/aggregator readers behave (new arrivals surface regardless of original date); the visible publish date avoids real deception.
- Fix root causes instead — cron reliability (gaps in daily ingest) and the known new-source-pulls-entire-backlog bug (`docs/v2_features.md` doesn't currently track this one — see `ingest/handler.py::_process_source`, `last_known_guid` is `None` for a brand-new source so nothing stops the full-feed pull) — shrinks how often this scenario happens rather than changing the ranking formula.

**Not yet decided** — user wants to think about this more before choosing an approach.

---


