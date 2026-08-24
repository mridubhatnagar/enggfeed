"""One-off script to apply the exported local test-ingest data (see
export_ingest_test_data.py) to another environment's DB — written for
syncing the local BackgroundTasks-fix verification run to the server.

Blogs are matched by guid (skip if already present — handles the server
having independently ingested the same article). Tags and prerequisites
are matched by name/topic_name, NOT copied by id, since local and server
ids are not guaranteed to align — only genuinely new ones are inserted.
Writes go through the Service/DAO layers so cache invalidation stays
correct (see PrerequisiteDAO.update's @cache.set decorator).

Usage:
    docker exec -it app_enggsystemfeed python apply_ingest_test_data.py ingest_test_data_export.json
"""

import sys
from datetime import datetime

from blog.dao import BlogDAO, BlogSourceDAO
from blog.models import Blog
from blog.service import BlogService, BlogSourceService
from database import SessionLocal
from ingest.dao import LLMUsageDAO
from ingest.service import LLMUsageService
from prerequisites.dao import BlogPrerequisiteDAO, PrerequisiteDAO
from prerequisites.service import BlogPrerequisiteService, PrerequisiteService
from simplify.dao import SimplifyDAO
from simplify.service import SimplifyService
from summary.dao import SummaryDAO
from summary.service import SummaryService
from tags.dao import BlogTagDAO, TagDAO
from tags.service import BlogTagService, TagService


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python apply_ingest_test_data.py <export.json>")
        sys.exit(1)

    import json

    with open(sys.argv[1]) as f:
        export = json.load(f)

    db = SessionLocal()
    blog_service = BlogService(BlogDAO(db))
    blog_source_service = BlogSourceService(BlogSourceDAO(db))
    tag_service = TagService(TagDAO(db))
    blog_tag_service = BlogTagService(BlogTagDAO(db))
    prerequisite_service = PrerequisiteService(PrerequisiteDAO(db))
    blog_prerequisite_service = BlogPrerequisiteService(BlogPrerequisiteDAO(db))
    summary_service = SummaryService(SummaryDAO(db))
    simplify_service = SimplifyService(SimplifyDAO(db))
    llm_usage_service = LLMUsageService(LLMUsageDAO(db))

    try:
        inserted = skipped = 0
        tags_created = tags_matched = 0
        prereqs_created = prereqs_matched = prereqs_content_backfilled = 0

        for i, b in enumerate(export["blogs"], 1):
            if blog_service.get_blog_by_guid(b["guid"]):
                print(
                    f"  [{i}/{len(export['blogs'])}] skip (guid exists): '{b['title']}'"
                )
                skipped += 1
                continue

            source = blog_source_service.get_source_by_name(b["source_name"])
            if source is None:
                print(
                    f"  [{i}/{len(export['blogs'])}] SKIP — source not found on this "
                    f"server: '{b['source_name']}'"
                )
                skipped += 1
                continue

            blog = Blog(
                guid=b["guid"],
                link=b["link"],
                title=b["title"],
                thumbnail=b["thumbnail"],
                word_count=b["word_count"],
                published_at=(
                    datetime.fromisoformat(b["published_at"])
                    if b["published_at"]
                    else None
                ),
                created_at=datetime.fromisoformat(b["created_at"]),
                blog_source_id=source.id,
            )
            blog_service.insert_blog(blog)
            blog_id = blog.id

            for t in b["tags"]:
                existing = tag_service.get_tag_by_name(t["tag"])
                if existing is None:
                    existing = tag_service.create_tag(t["tag"], t["embedding"])
                    tags_created += 1
                else:
                    tags_matched += 1
                blog_tag_service.create_blog_tag(blog_id, existing.tag_id)

            for p in b["prerequisites"]:
                existing = prerequisite_service.get_prerequisite_by_topic_name(
                    p["topic_name"], use_cache=False
                )
                if existing is None:
                    existing = prerequisite_service.create_prerequisite(
                        p["topic_name"], p["embedding"]
                    )
                    if p["content"] is not None:
                        existing = prerequisite_service.update_prerequisite(
                            p["topic_name"], p["content"]
                        )
                    prereqs_created += 1
                else:
                    prereqs_matched += 1
                    if existing.content is None and p["content"] is not None:
                        existing = prerequisite_service.update_prerequisite(
                            p["topic_name"], p["content"]
                        )
                        prereqs_content_backfilled += 1
                blog_prerequisite_service.create_blog_prerequisite(blog_id, existing.id)

            if b["summary"] is not None:
                summary_service.create_summary(blog_id, b["summary"]["content"])

            if b["simplify"] is not None:
                simplify_service.create_simplify(blog_id, b["simplify"]["simplify"])

            for u in b["llm_usage"]:
                llm_usage_service.create_llm_usage(
                    blog_id=blog_id,
                    call_type=u["call_type"],
                    provider=u["provider"],
                    model=u["model"],
                    input_tokens=u["input_tokens"],
                    output_tokens=u["output_tokens"],
                    total_tokens=u["total_tokens"],
                    cost_usd=u["cost_usd"],
                )

            print(f"  [{i}/{len(export['blogs'])}] inserted: '{b['title']}'")
            inserted += 1

        print()
        print(f"blogs: inserted={inserted} skipped={skipped}")
        print(f"tags: created={tags_created} matched_existing={tags_matched}")
        print(
            f"prerequisites: created={prereqs_created} matched_existing={prereqs_matched} "
            f"content_backfilled={prereqs_content_backfilled}"
        )

        import sqlalchemy as sa

        for source_name in export.get("removed_sources", []):
            source_row = db.execute(
                sa.text("SELECT id FROM blog_source WHERE source = :s"),
                {"s": source_name},
            ).first()
            if source_row is None:
                print(f"removed_sources: '{source_name}' already absent, nothing to do")
                continue
            ref_count = db.execute(
                sa.text("SELECT count(*) FROM blog WHERE blog_source_id = :id"),
                {"id": source_row.id},
            ).scalar()
            if ref_count > 0:
                print(
                    f"removed_sources: SKIP '{source_name}' — {ref_count} blog row(s) "
                    "reference it on this server, not deleting"
                )
                continue
            db.execute(
                sa.text("DELETE FROM blog_source WHERE id = :id"), {"id": source_row.id}
            )
            db.commit()
            print(f"removed_sources: deleted '{source_name}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
