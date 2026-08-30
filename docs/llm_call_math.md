# LLM Call Count Per Blog

Reference math for how many LLM/embedding calls one blog generates during ingest, worked out while reconciling `llm_usage` data on 2026-08-28.

## Per-blog call breakdown (FULL tier)

| Call | Count | Notes |
|------|-------|-------|
| `tag_prerequisite_extraction` | 1 | Single `INGEST_PROMPT` call returns both `tags` and `prerequisites` together — not 2 separate calls |
| `tag_embedding` | ~5 | One embedding call per tag candidate returned by extraction, always fires (needed to check similarity, not just to store new ones) |
| `prerequisite_embedding` | ~5 | Same, per prerequisite candidate |
| `prerequisite_content` | 0-5 | Only fires for candidates with **no** existing similar prerequisite (cosine similarity < 0.88 threshold against the `prerequisite` table). Matched candidates reuse existing content, no call. Tags have no equivalent — a tag is just a label, a prerequisite is a full generated explanation. |
| `summary` | 1 | Always, for PARTIAL/FULL tier |
| `simplify` | 1 | FULL tier only |

**Ceiling (all 5 prerequisites are brand-new topics):** `1 + 5 + 5 + 5 + 1 + 1 = 18 calls`
**Typical (~60% of prerequisites are new, observed 2026-08-27/28 batch):** `1 + 5 + 5 + 3 + 1 + 1 ≈ 16 calls`
**PARTIAL tier (no simplify):** ceiling `1 + 5 + 5 + 5 + 1 = 17`, typical ≈ 15
**LIMITED tier:** 0 calls — skips all LLM/embedding calls by design (`word_count < CONTENT_TIER_LIMITED_MAX_WORDS`)

## Why call count looks high but cost stays low

Embedding calls (`tag_embedding`, `prerequisite_embedding`) dominate call *count* (10 of the ~16-18 per blog) but are effectively free — `text-embedding-3-small` costs $0.02/Mtok, and a tag/prerequisite name is a handful of tokens. Real cost comes from the generation calls: `tag_prerequisite_extraction`, `summary`, `simplify` (all per-blog), and `prerequisite_content` (per new topic, not per blog — reused across every future blog that references the same prerequisite once generated).

## Worked example — 2026-08-28 backfill

8 distinct blogs got LLM calls (7 needed tag/prerequisite extraction, all 8 needed summary+simplify):

| call_type | calls | cost_usd |
|---|---|---|
| `tag_prerequisite_extraction` | 7 | 0.09971400 |
| `tag_embedding` | 35 | 0.00000230 |
| `prerequisite_embedding` | 35 | 0.00000204 |
| `prerequisite_content` | 21 | 0.14002800 |
| `summary` | 8 | 0.03625700 |
| `simplify` | 8 | 0.11152800 |
| **Total** | **114** | **0.38753134** |

114 calls / 8 blogs ≈ 14.25 calls/blog average — consistent with the typical-case estimate above, with `prerequisite_content` ending up the single priciest call type that day (21 of the 35 prerequisite candidates were genuinely new topics).

## Per-blog $ cost (worst case)

Per-call average cost, derived from the worked example above (`cost_usd / calls` per call_type):

| Call | Avg cost/call | Worst-case count | Subtotal |
|---|---|---|---|
| `tag_prerequisite_extraction` | $0.0142449 | 1 | $0.0142449 |
| `tag_embedding` | $0.0000000657 | 5 | $0.0000003 |
| `prerequisite_embedding` | $0.0000000583 | 5 | $0.0000003 |
| `prerequisite_content` | $0.006668 | 5 | $0.033340 |
| `summary` | $0.0045321 | 1 | $0.0045321 |
| `simplify` | $0.013941 | 1 | $0.013941 |
| **Total (18 calls, worst case)** | | | **≈ $0.0661/blog (≈ ₹6.31, at ₹95.44/USD from `cost_log.md`)** |

Typical case (16 calls, 3 of 5 prerequisites new instead of 5): **≈ $0.0527/blog (≈ ₹5.03)**.

`prerequisite_content` dominates worst-case cost (~50% of it) since it's the only call type that scales with topic novelty rather than firing a flat once-per-blog — embeddings stay essentially free regardless.
