"""
One-off script to backfill summary/simplify for articles ingested before
eager generation-at-ingest shipped. Skips articles whose RSS content has
already aged out of the feed window (logged, not treated as fatal).

Run:
    docker exec -it app_enggsystemfeed python backfill_summary_simplify.py
"""

from blog.models import Blog, BlogSource
from constants import CONTENT_TIER_LIMITED_MAX_WORDS, CONTENT_TIER_PARTIAL_MAX_WORDS
from database import SessionLocal
from exceptions import LLMUnreachableError, RSSFeedError
from prompts.simplify import SIMPLIFY_PROMPT
from prompts.summary import SUMMARY_PROMPT
from rss_client import RSSClient
from simplify.models import Simplify
from summary.models import Summary
from utils import call_llm


def backfill_summary(db, rss_client: RSSClient) -> tuple[int, int, int]:
    """Returns (created, aged_out, failed)."""
    blogs = (
        db.query(Blog)
        .outerjoin(Summary, Summary.blog_id == Blog.id)
        .filter(Blog.word_count >= CONTENT_TIER_LIMITED_MAX_WORDS)
        .filter(Summary.id.is_(None))
        .all()
    )
    created = aged_out = failed = 0
    for blog in blogs:
        source = (
            db.query(BlogSource).filter(BlogSource.id == blog.blog_source_id).first()
        )
        if source is None:
            print(f"  [skip] no source for blog '{blog.title}' ({blog.id})")
            failed += 1
            continue
        try:
            content = rss_client.get_content(source.rss_feed_link, blog.guid)
        except RSSFeedError:
            print(f"  [aged-out] summary: '{blog.title}' ({blog.id})")
            aged_out += 1
            continue

        try:
            prompt = SUMMARY_PROMPT.format(title=blog.title, content=content)
            llm_result = call_llm(prompt)
        except LLMUnreachableError as exc:
            print(f"  [failed] summary: '{blog.title}' ({blog.id}): {exc}")
            failed += 1
            continue

        summary_content = {
            "short_summary": llm_result.get("short_summary", ""),
            "key_points": llm_result.get("key_points", []),
        }
        db.add(Summary(blog_id=blog.id, content=summary_content))
        db.commit()
        print(f"  [created] summary: '{blog.title}' ({blog.id})")
        created += 1

    return created, aged_out, failed


def backfill_simplify(db, rss_client: RSSClient) -> tuple[int, int, int]:
    """Returns (created, aged_out, failed)."""
    blogs = (
        db.query(Blog)
        .outerjoin(Simplify, Simplify.blog_id == Blog.id)
        .filter(Blog.word_count >= CONTENT_TIER_PARTIAL_MAX_WORDS)
        .filter(Simplify.id.is_(None))
        .all()
    )
    created = aged_out = failed = 0
    for blog in blogs:
        source = (
            db.query(BlogSource).filter(BlogSource.id == blog.blog_source_id).first()
        )
        if source is None:
            print(f"  [skip] no source for blog '{blog.title}' ({blog.id})")
            failed += 1
            continue
        try:
            content = rss_client.get_content(source.rss_feed_link, blog.guid)
        except RSSFeedError:
            print(f"  [aged-out] simplify: '{blog.title}' ({blog.id})")
            aged_out += 1
            continue

        try:
            prompt = SIMPLIFY_PROMPT.format(title=blog.title, content=content)
            llm_result = call_llm(prompt)
        except LLMUnreachableError as exc:
            print(f"  [failed] simplify: '{blog.title}' ({blog.id}): {exc}")
            failed += 1
            continue

        simplify_content = llm_result.get("simplify", "")
        db.add(Simplify(blog_id=blog.id, simplify=simplify_content))
        db.commit()
        print(f"  [created] simplify: '{blog.title}' ({blog.id})")
        created += 1

    return created, aged_out, failed


def main() -> None:
    db = SessionLocal()
    rss_client = RSSClient()
    try:
        print("Backfilling summary...")
        s_created, s_aged, s_failed = backfill_summary(db, rss_client)
        print("Backfilling simplify...")
        p_created, p_aged, p_failed = backfill_simplify(db, rss_client)
    finally:
        db.close()

    print()
    print(f"summary:  created={s_created} aged_out={s_aged} failed={s_failed}")
    print(f"simplify: created={p_created} aged_out={p_aged} failed={p_failed}")


if __name__ == "__main__":
    main()
