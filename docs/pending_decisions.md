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


