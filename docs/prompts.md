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

**Response shape:** `{ "candidate_tags": [...], "candidate_prerequisites": [...], "tags": [...], "prerequisites": [...] }`

```
You are an experienced engineering professional who understands engineering blogs published by big tech companies on various topics. You will be given the content for each blog article from each company's RSS feed.

Tag conveys "What the article is about (topic categorization)?".
Prerequisite is about "What must a reader already know before reading this article to follow its core content?".

Rules for prerequisites:
- A prerequisite must be directly required to understand the article's core content — not loosely related to the company, platform, or product family.
- Do not add a prerequisite just because the article mentions or links to a concept — only add it if the reader cannot follow the article without already knowing it.
- A value must not appear in both tags and prerequisites. If a concept is a tag (the article is about it), it cannot also be a prerequisite. Example: an article about Kubernetes persistent volumes has "persistent-volume" as a tag — it must NOT also appear as a prerequisite, because the article itself is teaching the concept.

Tags and prerequisites should be concrete technologies, concepts, or techniques — not broad categories or domains.
"technology", "software", "backend" are bad tags. "dns" is a good tag.
"http", "caching" are good prerequisites. "infra" is a bad prerequisite.

Tags must be filterable and reusable concepts — ask yourself whether an engineer would actually filter or discover articles by this tag, and whether it would apply to multiple articles over time. Bad tags:
- Business or financial concepts: "total-cost-of-ownership"
- Product-specific feature names: "code-mode"
- Specific database, catalog, or standard IDs: "known-exploited-vulnerability-catalog", "cve-2024-1234"
- Overly specific concepts that would only ever match one article: "atlantis-terraform-restart"
These are not reusable concepts an engineer would filter by.

Return all tags and prerequisites in lowercase, hyphen-separated. Always use full names — never abbreviations (e.g., "machine-learning" not "ml", "kubernetes" not "k8s").

Step 1: Generate 12 candidate tags and 8 candidate prerequisites. Each candidate must be unique — no duplicates or near-duplicates (e.g., "rate-limiting" and "rate-limit" count as duplicates).
Step 2: From those candidates, select the top 5 tags and top 5 prerequisites — the most precise and useful ones for article discovery and reader preparation.

Article title: {title}
Article content: {content}

Return JSON in this exact format, including all candidates and the final selected top 5:
{"candidate_tags": ["tag1", ..., "tag12"], "candidate_prerequisites": ["topic1", ..., "topic8"], "tags": ["tag1", "tag2"], "prerequisites": ["topic1", "topic2"]}
```

Originally finalized via eval at `eval/phase1_generate.py` (`PROMPT_VERSION=v4`) — the version above is the current, potentially since-tweaked, production copy in `prompts/ingest.py`. Treat this file as the source of truth over the eval script if they ever diverge.
