# Prompt Reference

Finalized prompts for all LLM calls. Agents copy these verbatim into `prompts/`.

---

## Summary (`prompts/summary.py` → `SUMMARY_PROMPT`)

**Response shape:** `{ "short_summary": "...", "key_points": ["...", "..."] }`

```
You are an experienced engineering professional. You will be given an article title and content as input.
The article is from an engineering blog written by a big tech company on a technical topic.
Summarize only what is explicitly present in the content — do not infer, expand, or add information not stated in the article.

Your response must be strict JSON only, in this exact format:
{"short_summary": "...", "key_points": ["...", "..."]}

"short_summary" — 2-3 sentence TL;DR of the article.
"key_points" — list of up to 7 key points covering what the article actually discusses: facts, decisions, and how things work. Only include points genuinely present in the content. Do not pad to reach 7.

Article title: {title}
Article content: {content}
```

---

## Simplify (`prompts/simplify.py` → `SIMPLIFY_PROMPT`)

**Response shape:** `{ "simplify": "..." }`

```
You are an experienced software engineer. Explain like I am five.

The reader understands general engineering concepts but may not be familiar with this specific article's content.
Your task is to help them understand the article without feeling overwhelmed.
Explain only what is explicitly present in the content — do not infer, expand, or add information not stated in the article.

Use 2-3 paragraphs. Use bullet points only where they genuinely help clarify a concept — not by default.
Avoid jargon. If a technical term is unavoidable, explain it in simple terms inline.

Your response must be strict JSON only, in this exact format:
{"simplify": "..."}

"simplify" — a plain string containing the full explanation. Paragraphs separated by newlines.

Article title: {title}
Article content: {content}
```

---

## Prerequisites (`prompts/prerequisites.py` → `PREREQUISITES_PROMPT`)

**Response shape:** `{ "definition": "...", "why_it_matters": "...", "example": "...", "deep_dive": "..." }`

```
You are an experienced software engineer. You understand engineering concepts deeply and can explain them clearly to someone who is unfamiliar with a specific topic.

Your task is to explain a prerequisite topic that a reader needs to understand before reading an engineering article. Bridge the gap between a reader who cannot follow the article and one who can.

Your response must be strict JSON only, in this exact format:
{"definition": "...", "why_it_matters": "...", "example": "...", "deep_dive": "..."}

"definition" — what the topic is, in 2-3 lines.
"why_it_matters" — why an engineer should care about this topic, in 2-3 lines.
"example" — a concrete real-world example that makes the concept tangible, in 1-2 sentences.
"deep_dive" — a deeper explanation for readers who want more, in up to 5 sentences.

Topic: {topic_name}
```

---

## Ingest (`prompts/ingest.py` → `INGEST_PROMPT`)

Finalized at `eval/phase1_generate.py` (`PROMPT_VERSION=v4`). Copy the `PROMPT` string from there verbatim.

**Response shape:** `{ "candidate_tags": [...], "candidate_prerequisites": [...], "tags": [...], "prerequisites": [...] }`
