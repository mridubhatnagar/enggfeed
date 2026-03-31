# Pending Decisions

---

## LLM Model Choice

**Question:** Claude Sonnet 4.6 or GPT-4.1?

| | Sonnet 4.6 | GPT-4.1 |
|---|---|---|
| Input | $3.00/Mtok | $2.00/Mtok |
| Output | $15.00/Mtok | $8.00/Mtok |
| Cache read | $0.15/Mtok | $0.50/Mtok |

- Cost is negligible at this project's scale either way
- Sonnet has cheaper cache reads — relevant for ingest where system prompt is reused
- Sonnet keeps the stack simpler (one vendor, one SDK)
- **Quality is undecided** — run evals on both before deciding. Key thing to check: structured JSON output reliability for tag and prerequisite extraction, since that feeds directly into the normalization pipeline.
- Use Anthropic Console and OpenAI Playground with the same prompt on 10-15 real RSS articles, compare outputs side by side.

---



## Tagging Pipeline

**Question:** Which LLM model for tagging, and what does the prompt look like?

- Tags are LLM freeform — normalization via embedding + cosine similarity (threshold: 0.95) at ingest. See `docs/tech_decisions.md` Tags section.
- Open question: whether to feed existing RSS `<category>` values to LLM as hints — decide after evaluating tagging quality in practice
- Prompt lives in `prompts/ingest.py`

**TODO — validate before implementing:**
1. Write tagging prompt in `prompts/ingest.py`
2. Manually copy content from 10–15 RSS feed entries across different sources
3. Run in Anthropic Console Evaluation Tool — feed article content as `{{ARTICLE_CONTENT}}` variable, review tag output
4. Iterate on prompt until satisfied, then lock for v1

Same eval approach applies to `prompts/summary.py` and `prompts/prerequisites.py` before integrating into the project.

---


