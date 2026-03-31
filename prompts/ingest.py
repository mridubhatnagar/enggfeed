INGEST_PROMPT = """You are an experienced engineering professional who understands engineering blogs published by big tech companies on various topics. You will be given the content for each blog article from each company's RSS feed.

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
{{"candidate_tags": ["tag1", ..., "tag12"], "candidate_prerequisites": ["topic1", ..., "topic8"], "tags": ["tag1", "tag2"], "prerequisites": ["topic1", "topic2"]}}"""
