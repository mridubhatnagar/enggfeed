"""One-off script to compare Claude Sonnet 4.6 vs GPT-5.6 Terra output quality
on real article content, side by side — used to decide whether to switch the
ingest pipeline's LLM provider away from Anthropic (blocked by a pending AWS
Bedrock account approval) to OpenAI.

Picks N recent FULL-tier blogs from the local DB, re-fetches their live RSS
content (raw content isn't stored per the project's design), and runs the
same three prompts (tag/prerequisite extraction, summary, simplify) through
both models for direct comparison.

Usage:
    docker exec -it app_enggsystemfeed python compare_llm_models.py [N]
"""

import json
import sys

import anthropic
import openai

from config import settings
from constants import CONTENT_TIER_PARTIAL_MAX_WORDS
from database import SessionLocal
from exceptions import RSSFeedError
from prompts.ingest import INGEST_PROMPT
from prompts.simplify import SIMPLIFY_PROMPT
from prompts.summary import SUMMARY_PROMPT
from rss_client import RSSClient

_GPT_MODEL = "gpt-5.6-terra"
_CLAUDE_MODEL = "claude-sonnet-4-6"


def call_claude(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30)
    message = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        system="Return only valid JSON. Do not include any explanation or prose outside the JSON object.",
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return json.loads(raw)


def call_gpt(prompt: str) -> dict:
    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=_GPT_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON. Do not include any explanation or prose outside the JSON object.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()
    return json.loads(raw)


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8

    db = SessionLocal()
    rss_client = RSSClient()
    try:
        import sqlalchemy as sa

        rows = db.execute(
            sa.text(
                "SELECT b.guid, b.title, b.word_count, bs.rss_feed_link "
                "FROM blog b JOIN blog_source bs ON bs.id = b.blog_source_id "
                "WHERE b.word_count >= :min_words "
                "ORDER BY b.created_at DESC LIMIT :n"
            ),
            {"min_words": CONTENT_TIER_PARTIAL_MAX_WORDS, "n": n},
        ).fetchall()

        print(
            f"Comparing {len(rows)} article(s) — Claude ({_CLAUDE_MODEL}) vs GPT ({_GPT_MODEL})\n"
        )

        for i, row in enumerate(rows, 1):
            print("=" * 100)
            print(f"[{i}/{len(rows)}] {row.title}")
            print("=" * 100)

            try:
                content = rss_client.get_content(row.rss_feed_link, row.guid)
            except RSSFeedError as exc:
                print(f"  SKIP — content no longer available in feed: {exc}\n")
                continue

            for label, prompt_template, needs_full in [
                ("TAGS/PREREQUISITES", INGEST_PROMPT, False),
                ("SUMMARY", SUMMARY_PROMPT, False),
                ("SIMPLIFY", SIMPLIFY_PROMPT, False),
            ]:
                prompt = prompt_template.format(title=row.title, content=content)
                print(f"\n--- {label} ---")
                try:
                    claude_result = call_claude(prompt)
                    print(f"CLAUDE:\n{json.dumps(claude_result, indent=2)}")
                except Exception as exc:
                    print(f"CLAUDE FAILED: {exc}")

                try:
                    gpt_result = call_gpt(prompt)
                    print(f"\nGPT:\n{json.dumps(gpt_result, indent=2)}")
                except Exception as exc:
                    print(f"GPT FAILED: {exc}")
                print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
