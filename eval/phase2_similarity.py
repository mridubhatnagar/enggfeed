"""
Phase 2: Embed seed tags and prerequisites, fetch RSS from Cloudflare/GitHub/Meta/AWS/Slack, call Claude to generate
new tags and prerequisites, compute cosine similarity against seed embeddings, write phase2_similarity.json,
and upload to Braintrust for labeling.

After labeling in Braintrust: mark each row "merge" or "separate",
then pick the similarity threshold where decisions look right.
"""

import json
import os
import feedparser
import anthropic
import braintrust
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
# BRAINTRUST_API_KEY = os.environ["BRAINTRUST_API_KEY"]

BRAINTRUST_PROJECT = "enggsystemfeed-eval"
BRAINTRUST_DATASET = "phase2-similarity"

EMBEDDING_MODEL = "text-embedding-3-small"
MAX_ARTICLES_PER_FEED = 10

RSS_FEEDS = {
    "cloudflare": "https://blog.cloudflare.com/rss/",
    "github": "https://github.blog/feed/",
    "meta": "https://engineering.fb.com/feed/",
    "aws": "https://aws.amazon.com/blogs/aws/feed/",
    "slack": "https://slack.engineering/feed/",
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


def embed_text(text: str, client: OpenAI) -> list[float]:
    response = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


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
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    parsed = json.loads(raw)
    return {
        "tags": parsed.get("tags", []),
        "prerequisites": parsed.get("prerequisites", []),
    }


def find_closest_seed(
    embedding: list[float],
    seed_embeddings: list[tuple[str, list[float]]],
) -> tuple[str, float]:
    best_value = None
    best_score = -1.0
    for seed_value, seed_emb in seed_embeddings:
        score = cosine_similarity(embedding, seed_emb)
        if score > best_score:
            best_score = score
            best_value = seed_value
    return best_value, best_score


def main():
    eval_dir = os.path.dirname(__file__)

    seed_tags_path = os.path.join(eval_dir, "seed_tags.json")
    if not os.path.exists(seed_tags_path):
        raise FileNotFoundError("seed_tags.json not found — run phase1_export_seeds.py first")

    seed_prerequisites_path = os.path.join(eval_dir, "seed_prerequisites.json")
    if not os.path.exists(seed_prerequisites_path):
        raise FileNotFoundError("seed_prerequisites.json not found — run phase1_export_seeds.py first")

    with open(seed_tags_path) as f:
        seed_tags: list[str] = json.load(f)

    with open(seed_prerequisites_path) as f:
        seed_prerequisites: list[str] = json.load(f)

    print(f"Loaded {len(seed_tags)} seed tags, {len(seed_prerequisites)} seed prerequisites")

    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    # Embed seed tags
    print("Embedding seed tags...")
    seed_tag_embeddings: list[tuple[str, list[float]]] = []
    for tag in seed_tags:
        emb = embed_text(tag, openai_client)
        seed_tag_embeddings.append((tag, emb))
    print(f"Embedded {len(seed_tag_embeddings)} seed tags")

    # Embed seed prerequisites
    print("Embedding seed prerequisites...")
    seed_prereq_embeddings: list[tuple[str, list[float]]] = []
    for prereq in seed_prerequisites:
        emb = embed_text(prereq, openai_client)
        seed_prereq_embeddings.append((prereq, emb))
    print(f"Embedded {len(seed_prereq_embeddings)} seed prerequisites")

    similarity_rows = []

    for company, feed_url in RSS_FEEDS.items():
        print(f"\nFetching RSS: {company}...")
        articles = fetch_articles(feed_url, MAX_ARTICLES_PER_FEED)
        print(f"  {len(articles)} articles fetched")

        for article in articles:
            if not article["content"].strip():
                print(f"  Skipping (no content): {article['title'][:60]}")
                continue
            print(f"  Processing: {article['title'][:60]}")
            try:
                llm_output = call_claude(article["title"], article["content"], anthropic_client)

                for new_tag in llm_output["tags"]:
                    if new_tag in seed_tags:
                        continue
                    new_emb = embed_text(new_tag, openai_client)
                    canonical_value, similarity_score = find_closest_seed(new_emb, seed_tag_embeddings)
                    similarity_rows.append({
                        "type": "tag",
                        "new_value": new_tag,
                        "canonical_value": canonical_value,
                        "similarity_score": round(similarity_score, 4),
                        "feedback": None,
                    })

                for new_prereq in llm_output["prerequisites"]:
                    if new_prereq in seed_prerequisites:
                        continue
                    new_emb = embed_text(new_prereq, openai_client)
                    canonical_value, similarity_score = find_closest_seed(new_emb, seed_prereq_embeddings)
                    similarity_rows.append({
                        "type": "prerequisite",
                        "new_value": new_prereq,
                        "canonical_value": canonical_value,
                        "similarity_score": round(similarity_score, 4),
                        "feedback": None,
                    })

            except Exception as e:
                print(f"  Error: {e}")
                continue

    # Sort by similarity score descending for easier review
    similarity_rows.sort(key=lambda r: r["similarity_score"], reverse=True)

    output_path = os.path.join(eval_dir, "phase2_similarity.json")
    with open(output_path, "w") as f:
        json.dump(similarity_rows, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(similarity_rows)} rows to phase2_similarity.json")

    # Upload to Braintrust — commented out, upload phase2_similarity.json manually via Braintrust dashboard
    # print("Uploading to Braintrust...")
    # braintrust.login(api_key=BRAINTRUST_API_KEY)
    # dataset = braintrust.init_dataset(project=BRAINTRUST_PROJECT, name=BRAINTRUST_DATASET)
    # for row in similarity_rows:
    #     dataset.insert(
    #         input={
    #             "type": row["type"],
    #             "new_value": row["new_value"],
    #             "canonical_value": row["canonical_value"],
    #             "similarity_score": row["similarity_score"],
    #         },
    #         expected={},
    #     )
    # dataset.flush()
    # print(f"Uploaded {len(similarity_rows)} rows to Braintrust project '{BRAINTRUST_PROJECT}', dataset '{BRAINTRUST_DATASET}'")
    print("Label each row 'merge' or 'separate' in Braintrust, then pick your threshold.")


if __name__ == "__main__":
    main()
