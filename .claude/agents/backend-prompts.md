---
name: backend-prompts
description: Writes stubs for all four prompt files — summary, simplify, prerequisites, ingest. None are implemented until eval is complete.
---

# Backend Prompts Sub-agent

## Scope
Create exactly these files:
- `prompts/summary.py` — stub only
- `prompts/simplify.py` — stub only
- `prompts/prerequisites.py` — stub only
- `prompts/ingest.py` — stub only

Do not create any other files. Do not modify any existing files.

## Mandatory reads before starting
- `docs/pending_decisions.md` — explains why all prompts are stubs pending eval
- `docs/tech_decisions.md` — LLM best practices, JSON-only constraint, expected response shapes per handler

## Hard rules
- Do not implement any prompt. All four files are stubs.
- The stub format is the same for all files — see below.
- Do not add any variables or functions beyond the stub.
- If anything is unclear, stop and ask.

---

## Files

### `prompts/summary.py`
```python
# TODO: Prompt pending eval before implementation.
# See docs/pending_decisions.md.
# Test across 10–15 real RSS articles in Anthropic Console before implementing.
# Expected response shape: { "summary": "..." }

SUMMARY_PROMPT = None
```

### `prompts/simplify.py`
```python
# TODO: Prompt pending eval before implementation.
# See docs/pending_decisions.md.
# Test across 10–15 real RSS articles in Anthropic Console before implementing.
# Expected response shape: { "simplify": "..." }

SIMPLIFY_PROMPT = None
```

### `prompts/prerequisites.py`
```python
# TODO: Prompt pending eval before implementation.
# See docs/pending_decisions.md.
# Test across 10–15 real RSS articles in Anthropic Console before implementing.
# Expected response shape: { "definition": "...", "why_it_matters": "...", "example": "...", "deep_dive": "..." }

PREREQUISITES_PROMPT = None
```

### `prompts/ingest.py`
```python
# TODO: Prompt pending eval before implementation.
# See docs/pending_decisions.md — Tagging Pipeline section.
# Test across 10–15 real RSS articles in Anthropic Console before implementing.
# Expected response shape: { "tags": [...], "prerequisites": [...] }

INGEST_PROMPT = None
```

---

## Checkpoint — pause here
Stop. Notify the user to verify:
- All four files exist under `prompts/`
- App starts without ImportError from any module importing these stubs (`docker compose logs app`)
