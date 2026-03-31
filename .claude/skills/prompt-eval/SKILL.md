---
name: prompt-eval
description: Guide writing and evaluating the 4 LLM prompts for enggsystemfeed — ingest, summary, simplify, prerequisites.
---

Guide the user through writing and evaluating the prompt specified in $ARGUMENTS.
Valid values: `ingest`, `summary`, `simplify`, `prerequisites`.
If $ARGUMENTS is empty, ask which prompt to work on.

Read `docs/pending_decisions.md` before starting — it contains open questions relevant to the ingest prompt.

---

## Prompt specs

### `ingest` — `prompts/ingest.py` → `INGEST_PROMPT`
**Purpose:** Given a full article text, extract:
1. Tags (3–7 short topic labels, e.g. "distributed-systems", "caching", "kubernetes")
2. Prerequisite topics (2–5 concepts the reader must know, e.g. "TCP/IP", "B-trees")

**Required JSON output shape:**
```json
{
  "tags": ["tag-one", "tag-two"],
  "prerequisites": ["Topic One", "Topic Two"]
}
```

**Tag rules:** lowercase, hyphen-separated, no spaces. 3–7 tags per article.
**Prerequisite rules:** Title Case, short noun phrases. 2–5 prerequisites per article.
**Constraint:** JSON only — no explanation, no markdown, no preamble.

---

### `summary` — `prompts/summary.py` → `SUMMARY_PROMPT`
**Purpose:** Summarise a technical blog article for an engineering audience.

**Required JSON output shape:**
```json
{ "summary": "..." }
```

**Constraints:** JSON only. Summary should be concise but complete — cover the main idea, key technical points, and any notable conclusions. Preserve technical accuracy.

---

### `simplify` — `prompts/simplify.py` → `SIMPLIFY_PROMPT`
**Purpose:** Explain a technical blog article in plain English (ELI5 style) — suitable for someone outside the field.

**Required JSON output shape:**
```json
{ "simplify": "..." }
```

**Constraints:** JSON only. Avoid jargon. Use analogies. Keep it short and engaging.

---

### `prerequisites` — `prompts/prerequisites.py` → `PREREQUISITES_PROMPT`
**Purpose:** Given a topic name (e.g. "consistent hashing"), generate:
- `definition` — one-sentence plain English explanation
- `why_it_matters` — one paragraph: why engineers care about this
- `example` — one concrete real-world example
- `deep_dive` — deeper technical explanation for those who want more

**Required JSON output shape:**
```json
{
  "definition": "...",
  "why_it_matters": "...",
  "example": "...",
  "deep_dive": "..."
}
```

**Constraints:** JSON only. All 4 fields always present and non-empty.

---

## Eval process

Work through these steps with the user:

### Step 1 — Draft
Write a draft prompt. Include:
- A system message: instructs the LLM to return JSON only, no explanation, no markdown.
- A user message: provides the input (article text or topic name) and restates the output shape.

### Step 2 — Test cases
For the prompt being evaluated, define appropriate test cases:
- **ingest**: 5 articles — one very short (limited tier), one long detailed post, one tutorial, one opinion piece, one infrastructure/ops post
- **summary**: 3 articles — short, medium, long. Verify summary length is proportional.
- **simplify**: 3 articles — one highly technical, one moderate, one already simple. Verify jargon is removed.
- **prerequisites**: 5 topics — one very common (e.g. "REST API"), one niche (e.g. "CRDT"), one broad (e.g. "databases"), one narrow (e.g. "WAL in PostgreSQL"), one ambiguous (e.g. "consistency").

### Step 3 — Run in Anthropic Console
Test each case in the Anthropic Console (console.anthropic.com) using `claude-sonnet-4-6`. Paste article text or topic name as the user message.

### Step 4 — Check output
For each test case verify:
- [ ] Response is valid JSON (parseable)
- [ ] All required fields are present and non-empty
- [ ] Field values match the expected shape (e.g. tags are lowercase-hyphenated, prerequisites are Title Case)
- [ ] No extra fields, no preamble, no explanation outside the JSON
- [ ] Content quality is acceptable — accurate, well-scoped, not hallucinated

### Step 5 — Iterate or approve
- If any test case fails: identify the failure pattern, adjust the prompt, re-run that test case.
- If all pass: prompt is approved. Update `prompts/<name>.py` — replace the `None` stub with the real prompt string.

### Step 6 — Final check
After writing the prompt to file:
- Confirm `INGEST_PROMPT` / `SUMMARY_PROMPT` / etc. is a non-None string.
- Confirm the JSON shape in the prompt matches the handler's parsing code.
- Mark the prompt as done in `SETUP.md`.
