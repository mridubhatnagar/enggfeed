"""
One-off script to backfill tags/prerequisites for articles that were
inserted but got zero of both — e.g. because the embeddings API was
out of quota when the article was originally ingested. Re-derives the
tag/prerequisite candidate list via a fresh LLM call (the original list
isn't persisted anywhere), then reuses IngestHandler's real
_process_tag/_process_prerequisite methods so the normalization logic
can't drift from the production pipeline.

Skips articles whose RSS content has already aged out of the feed
window (logged, not treated as fatal) — same caveat as
backfill_summary_simplify.py.

Run:
    docker exec -it app_enggsystemfeed python backfill_tags_prerequisites.py
"""

from blog.dao import BlogDAO, BlogSourceDAO
from blog.models import Blog, BlogSource
from blog.service import BlogService, BlogSourceService
from constants import CONTENT_TIER_LIMITED_MAX_WORDS
from database import SessionLocal
from exceptions import LLMUnreachableError, RSSFeedError
from ingest.dao import LLMUsageDAO
from ingest.embedder import Embedder
from ingest.handler import IngestHandler
from ingest.models import LLMUsageCallType
from ingest.service import LLMUsageService
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.models import BlogPrerequisite
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from prompts.ingest import INGEST_PROMPT
from rss_client import RSSClient
from simplify.dao import SimplifyDAO
from simplify.service import SimplifyService
from summary.dao import SummaryDAO
from summary.service import SummaryService
from tags.dao import BlogTagDAO, TagDAO
from tags.models import BlogTag
from tags.service import BlogTagService, TagService
from utils import call_llm


def find_missing(db):
    return (
        db.query(Blog)
        .outerjoin(BlogTag, BlogTag.blog_id == Blog.id)
        .outerjoin(BlogPrerequisite, BlogPrerequisite.blog_id == Blog.id)
        .filter(Blog.word_count >= CONTENT_TIER_LIMITED_MAX_WORDS)
        .filter(BlogTag.blog_id.is_(None))
        .filter(BlogPrerequisite.blog_id.is_(None))
        .all()
    )


def main() -> None:
    db = SessionLocal()
    rss_client = RSSClient()
    handler = IngestHandler(
        blog_source_service=BlogSourceService(BlogSourceDAO(db)),
        blog_service=BlogService(BlogDAO(db)),
        tag_service=TagService(TagDAO(db)),
        blog_tag_service=BlogTagService(BlogTagDAO(db)),
        prerequisite_service=PrerequisiteService(PrerequisiteDAO(db)),
        blog_prerequisite_service=BlogPrerequisiteService(BlogPrerequisiteDAO(db)),
        summary_service=SummaryService(SummaryDAO(db)),
        simplify_service=SimplifyService(SimplifyDAO(db)),
        rss_client=rss_client,
        embedder=Embedder(),
        llm_usage_service=LLMUsageService(LLMUsageDAO(db)),
    )

    try:
        blogs = find_missing(db)
        print(f"Found {len(blogs)} blog(s) with zero tags and zero prerequisites.")

        created = aged_out = failed = 0
        for i, blog in enumerate(blogs, 1):
            source = (
                db.query(BlogSource)
                .filter(BlogSource.id == blog.blog_source_id)
                .first()
            )
            if source is None:
                print(f"  [{i}/{len(blogs)}] skip (no source): '{blog.title}'")
                failed += 1
                continue

            try:
                content = rss_client.get_content(source.rss_feed_link, blog.guid)
            except RSSFeedError:
                print(f"  [{i}/{len(blogs)}] aged-out: '{blog.title}'")
                aged_out += 1
                continue

            try:
                prompt = INGEST_PROMPT.format(title=blog.title, content=content)
                llm_result, usage = call_llm(prompt, return_usage=True)
            except LLMUnreachableError as exc:
                print(f"  [{i}/{len(blogs)}] failed: '{blog.title}': {exc}")
                failed += 1
                continue
            handler._record_chat_usage(
                blog.id, LLMUsageCallType.TAG_PREREQUISITE_EXTRACTION, usage
            )

            tags = llm_result.get("tags", [])
            prerequisites = llm_result.get("prerequisites", [])

            linked_tag_ids = set()
            for tag_name in tags:
                try:
                    handler._process_tag(blog.id, tag_name, linked_tag_ids)
                except Exception as exc:
                    print(f"    error processing tag '{tag_name}': {exc}")

            linked_prerequisite_ids = set()
            for topic_name in prerequisites:
                try:
                    handler._process_prerequisite(
                        blog.id, topic_name, linked_prerequisite_ids
                    )
                except Exception as exc:
                    print(f"    error processing prerequisite '{topic_name}': {exc}")

            print(
                f"  [{i}/{len(blogs)}] backfilled: '{blog.title}' "
                f"tags={len(linked_tag_ids)} prerequisites={len(linked_prerequisite_ids)}"
            )
            created += 1

        print()
        print(f"created={created} aged_out={aged_out} failed={failed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
