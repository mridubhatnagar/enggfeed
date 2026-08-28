"""
One-off script — permanently deletes the named blog_source rows and every
child row that depends on their Blog rows (blog_tag, blog_prerequisite,
llm_usage, summary, simplify), then the Blog rows themselves, then the
blog_source row. Shared Tag/Prerequisite vocabulary rows are NOT touched
(other blogs may still reference them).

Scope: Fly.io + Google (dead feedburner feed) only. Google Research is a
separate source and is not part of this purge.

Run:
    docker exec -it app_enggsystemfeed python purge_sources.py
"""

from blog.models import Blog, BlogSource
from database import SessionLocal
from ingest.models import LLMUsage
from prerequisites.models import BlogPrerequisite
from simplify.models import Simplify
from summary.models import Summary
from tags.models import BlogTag

SOURCES_TO_PURGE = ["Fly.io", "Google"]


def purge_source(db, source_name: str) -> None:
    source = db.query(BlogSource).filter(BlogSource.source == source_name).first()
    if source is None:
        print(f"  [skip] '{source_name}' — no blog_source row found")
        return

    blogs = db.query(Blog).filter(Blog.blog_source_id == source.id).all()
    blog_ids = [b.id for b in blogs]

    counts = {
        "blog_tag": 0,
        "blog_prerequisite": 0,
        "llm_usage": 0,
        "summary": 0,
        "simplify": 0,
    }
    if blog_ids:
        counts["blog_tag"] = (
            db.query(BlogTag)
            .filter(BlogTag.blog_id.in_(blog_ids))
            .delete(synchronize_session=False)
        )
        counts["blog_prerequisite"] = (
            db.query(BlogPrerequisite)
            .filter(BlogPrerequisite.blog_id.in_(blog_ids))
            .delete(synchronize_session=False)
        )
        counts["llm_usage"] = (
            db.query(LLMUsage)
            .filter(LLMUsage.blog_id.in_(blog_ids))
            .delete(synchronize_session=False)
        )
        counts["summary"] = (
            db.query(Summary)
            .filter(Summary.blog_id.in_(blog_ids))
            .delete(synchronize_session=False)
        )
        counts["simplify"] = (
            db.query(Simplify)
            .filter(Simplify.blog_id.in_(blog_ids))
            .delete(synchronize_session=False)
        )
        db.query(Blog).filter(Blog.blog_source_id == source.id).delete(
            synchronize_session=False
        )

    db.delete(source)
    db.commit()

    print(
        f"  [purged] '{source_name}' — {len(blog_ids)} blog(s), "
        f"blog_tag={counts['blog_tag']} blog_prerequisite={counts['blog_prerequisite']} "
        f"llm_usage={counts['llm_usage']} summary={counts['summary']} simplify={counts['simplify']}"
    )


def main() -> None:
    db = SessionLocal()
    try:
        for source_name in SOURCES_TO_PURGE:
            purge_source(db, source_name)
    finally:
        db.close()


if __name__ == "__main__":
    main()
