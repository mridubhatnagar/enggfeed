"""One-off script to compare Claude Sonnet 4.6 (direct Anthropic API, current
quality baseline) vs Qwen3 Coder Next (via Bedrock's mantle Chat Completions
endpoint, the only Bedrock model this account is actually authorized to
invoke) — to judge whether Qwen's output quality is acceptable as a
production substitute while Bedrock authorization for better models remains
blocked.

Picks N recent FULL-tier blogs from the local DB, re-fetches their live RSS
content (raw content isn't stored per the project's design), and runs the
same three prompts (tag/prerequisite extraction, summary, simplify) through
both models for direct comparison.

Reads BEDROCK_API_KEY from the environment (not from config.py/settings,
since this is a one-off script, not app code).

Usage:
    docker compose exec -e BEDROCK_API_KEY=<key> app python compare_qwen_quality.py [N]
"""

import json
import os
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

_CLAUDE_MODEL = "claude-sonnet-4-6"
_QWEN_MODEL = "qwen.qwen3-coder-next"
_QWEN_REGION = "ap-south-1"


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


def call_qwen(prompt: str, api_key: str) -> dict:
    client = openai.OpenAI(
        base_url=f"https://bedrock-mantle.{_QWEN_REGION}.api.aws/v1",
        api_key=api_key,
        timeout=30,
    )
    response = client.chat.completions.create(
        model=_QWEN_MODEL,
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

    api_key = os.environ.get("BEDROCK_API_KEY", "")
    if not api_key:
        raise SystemExit(
            "BEDROCK_API_KEY env var not set — pass it with "
            "`docker compose exec -e BEDROCK_API_KEY=<key> app python compare_qwen_quality.py`"
        )

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
            f"Comparing {len(rows)} article(s) — Claude ({_CLAUDE_MODEL}) vs Qwen ({_QWEN_MODEL})\n"
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

            for label, prompt_template in [
                ("TAGS/PREREQUISITES", INGEST_PROMPT),
                ("SUMMARY", SUMMARY_PROMPT),
                ("SIMPLIFY", SIMPLIFY_PROMPT),
            ]:
                prompt = prompt_template.format(title=row.title, content=content)
                print(f"\n--- {label} ---")
                try:
                    claude_result = call_claude(prompt)
                    print(f"CLAUDE:\n{json.dumps(claude_result, indent=2)}")
                except Exception as exc:
                    print(f"CLAUDE FAILED: {exc}")

                try:
                    qwen_result = call_qwen(prompt, api_key)
                    print(f"\nQWEN:\n{json.dumps(qwen_result, indent=2)}")
                except Exception as exc:
                    print(f"QWEN FAILED: {exc}")
                print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
