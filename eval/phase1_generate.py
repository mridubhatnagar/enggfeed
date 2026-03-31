"""
Phase 1: Fetch RSS from Cloudflare + GitHub, call Claude to generate tags and prerequisites,
flatten to one row per tag/prerequisite, write local JSON, upload to Braintrust.
"""

import json
import os
import feedparser
import anthropic
import braintrust
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
# BRAINTRUST_API_KEY = os.environ["BRAINTRUST_API_KEY"]

BRAINTRUST_PROJECT = "enggsystemfeed-eval"
BRAINTRUST_DATASET = "phase1-tags-prerequisites"

MAX_ARTICLES_PER_FEED = 15
PROMPT_VERSION = "v4"

RSS_FEEDS = {
    "cloudflare": "https://blog.cloudflare.com/rss/",
    "github": "https://github.blog/feed/",
}

PROMPT = """You are an experienced engineering professional who understands engineering blogs published by big tech companies on various topics. You will be given the content for each blog article from each company's RSS feed.

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


def fetch_articles(feed_url: str, max_articles: int) -> list[dict]:
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries[:max_articles]:
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary
        articles.append({
            "guid": entry.get("id", entry.get("link", "")),
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "content": content,
        })
    return articles


def call_claude(title: str, content: str, client: anthropic.Anthropic) -> dict:
    prompt = PROMPT.format(title=title, content=content)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    print(f"  LLM output: {raw[:2000]}")
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def flatten_to_rows(article: dict, llm_output: dict) -> list[dict]:
    rows = []
    candidate_tags = llm_output.get("candidate_tags", [])
    candidate_prerequisites = llm_output.get("candidate_prerequisites", [])
    for tag in llm_output.get("tags", []):
        rows.append({
            "input": {
                "title": article["title"],
                "guid": article["guid"],
                "link": article["link"],
                "type": "tag",
                "value": tag,
                "candidate_tags": candidate_tags,
                "prompt_version": PROMPT_VERSION,
            },
            "expected": {},
        })
    for prereq in llm_output.get("prerequisites", []):
        rows.append({
            "input": {
                "title": article["title"],
                "guid": article["guid"],
                "link": article["link"],
                "type": "prerequisite",
                "value": prereq,
                "candidate_prerequisites": candidate_prerequisites,
                "prompt_version": PROMPT_VERSION,
            },
            "expected": {},
        })
    return rows


def main():
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    all_rows = []

    for company, feed_url in RSS_FEEDS.items():
        print(f"Fetching RSS: {company}...")
        articles = fetch_articles(feed_url, MAX_ARTICLES_PER_FEED)
        print(f"  {len(articles)} articles fetched")

        for article in articles:
            if not article["content"].strip():
                print(f"  Skipping (no content): {article['title'][:60]}")
                continue
            print(f"  Processing: {article['title'][:60]}")
            try:
                llm_output = call_claude(article["title"], article["content"], anthropic_client)
                rows = flatten_to_rows(article, llm_output)
                all_rows.extend(rows)
            except Exception as e:
                print(f"  Error: {e}")
                continue

    output_path = os.path.join(os.path.dirname(__file__), "phase1_results.json")
    with open(output_path, "w") as f:
        json.dump(all_rows, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {len(all_rows)} rows to phase1_results.json")

    # Upload to Braintrust — commented out, upload phase1_results.json manually via Braintrust dashboard
    # print("Uploading to Braintrust...")
    # braintrust.login(api_key=BRAINTRUST_API_KEY)
    # dataset = braintrust.init_dataset(project=BRAINTRUST_PROJECT, name=BRAINTRUST_DATASET)
    # for row in all_rows:
    #     dataset.insert(input=row["input"], expected=row["expected"])
    # dataset.flush()
    # print(f"Uploaded {len(all_rows)} rows to Braintrust project '{BRAINTRUST_PROJECT}', dataset '{BRAINTRUST_DATASET}'")


if __name__ == "__main__":
    main()
