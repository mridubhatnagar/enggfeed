"""
One-off script to backfill summary/simplify for articles ingested before
eager generation-at-ingest shipped. Skips articles whose RSS content has
already aged out of the feed window (logged, not treated as fatal).

Run:
    docker exec -it app_enggsystemfeed python backfill_summary_simplify.py
"""

from blog.dao import BlogDAO, BlogSourceDAO
from blog.models import Blog, BlogSource
from blog.service import BlogService, BlogSourceService
from constants import (
    ANTHROPIC_SUMMARY_MODEL,
    CONTENT_TIER_LIMITED_MAX_WORDS,
    CONTENT_TIER_PARTIAL_MAX_WORDS,
)
from database import SessionLocal
from exceptions import LLMUnreachableError, RSSFeedError
from ingest.dao import LLMUsageDAO
from ingest.embedder import Embedder
from ingest.handler import IngestHandler
from ingest.models import LLMUsageCallType
from ingest.service import LLMUsageService
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from prompts.simplify import SIMPLIFY_PROMPT
from prompts.summary import SUMMARY_PROMPT
from rss_client import RSSClient
from simplify.dao import SimplifyDAO
from simplify.models import Simplify
from simplify.service import SimplifyService
from summary.dao import SummaryDAO
from summary.models import Summary
from summary.service import SummaryService
from tags.dao import BlogTagDAO, TagDAO
from tags.service import BlogTagService, TagService
from utils import call_llm


def build_handler(db) -> IngestHandler:
    return IngestHandler(
        blog_source_service=BlogSourceService(BlogSourceDAO(db)),
        blog_service=BlogService(BlogDAO(db)),
        tag_service=TagService(TagDAO(db)),
        blog_tag_service=BlogTagService(BlogTagDAO(db)),
        prerequisite_service=PrerequisiteService(PrerequisiteDAO(db)),
        blog_prerequisite_service=BlogPrerequisiteService(BlogPrerequisiteDAO(db)),
        summary_service=SummaryService(SummaryDAO(db)),
        simplify_service=SimplifyService(SimplifyDAO(db)),
        rss_client=RSSClient(),
        embedder=Embedder(),
        llm_usage_service=LLMUsageService(LLMUsageDAO(db)),
    )


def backfill_summary(
    db, rss_client: RSSClient, handler: IngestHandler
) -> tuple[int, int, int]:
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
            llm_result, usage = call_llm(
                prompt, return_usage=True, model=ANTHROPIC_SUMMARY_MODEL
            )
        except LLMUnreachableError as exc:
            print(f"  [failed] summary: '{blog.title}' ({blog.id}): {exc}")
            failed += 1
            continue
        handler._record_chat_usage(blog.id, LLMUsageCallType.SUMMARY, usage)

        summary_content = {
            "short_summary": llm_result.get("short_summary", ""),
            "key_points": llm_result.get("key_points", []),
        }
        db.add(Summary(blog_id=blog.id, content=summary_content))
        db.commit()
        print(f"  [created] summary: '{blog.title}' ({blog.id})")
        created += 1

    return created, aged_out, failed


def backfill_simplify(
    db, rss_client: RSSClient, handler: IngestHandler
) -> tuple[int, int, int]:
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
            llm_result, usage = call_llm(prompt, return_usage=True)
        except LLMUnreachableError as exc:
            print(f"  [failed] simplify: '{blog.title}' ({blog.id}): {exc}")
            failed += 1
            continue
        handler._record_chat_usage(blog.id, LLMUsageCallType.SIMPLIFY, usage)

        simplify_content = llm_result.get("simplify", "")
        db.add(Simplify(blog_id=blog.id, simplify=simplify_content))
        db.commit()
        print(f"  [created] simplify: '{blog.title}' ({blog.id})")
        created += 1

    return created, aged_out, failed


def main() -> None:
    db = SessionLocal()
    rss_client = RSSClient()
    handler = build_handler(db)
    try:
        print("Backfilling summary...")
        s_created, s_aged, s_failed = backfill_summary(db, rss_client, handler)
        print("Backfilling simplify...")
        p_created, p_aged, p_failed = backfill_simplify(db, rss_client, handler)
    finally:
        db.close()

    print()
    print(f"summary:  created={s_created} aged_out={s_aged} failed={s_failed}")
    print(f"simplify: created={p_created} aged_out={p_aged} failed={p_failed}")


if __name__ == "__main__":
    main()
