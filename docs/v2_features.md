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

