"""
One-off script to remove articles whose RSS content has permanently aged
out of the source feed and are still missing summary and/or simplify
(i.e. clicking Summary/Simplify on them will always 502). Run this after
backfill_summary_simplify.py has already recovered everything recoverable.

Deletes: blog_tag, blog_prerequisite, feedback, summary, simplify rows for
the affected blog, then the blog row itself (no ON DELETE CASCADE on these
FKs, so children must go first).

Run:
    docker exec -it app_enggsystemfeed python cleanup_aged_out_articles.py
"""

import socket

socket.setdefaulttimeout(15)

from blog.models import Blog, BlogSource
from constants import CONTENT_TIER_LIMITED_MAX_WORDS, CONTENT_TIER_PARTIAL_MAX_WORDS
from database import SessionLocal
from exceptions import RSSFeedError
from feedback.models import Feedback
from prerequisites.models import BlogPrerequisite
from rss_client import RSSClient
from simplify.models import Simplify
from summary.models import Summary
from tags.models import BlogTag


def find_missing_summary(db):
    return (
        db.query(Blog)
        .outerjoin(Summary, Summary.blog_id == Blog.id)
        .filter(Blog.word_count >= CONTENT_TIER_LIMITED_MAX_WORDS)
        .filter(Summary.id.is_(None))
        .all()
    )


def find_missing_simplify(db):
    return (
        db.query(Blog)
        .outerjoin(Simplify, Simplify.blog_id == Blog.id)
        .filter(Blog.word_count >= CONTENT_TIER_PARTIAL_MAX_WORDS)
        .filter(Simplify.id.is_(None))
        .all()
    )


def is_aged_out(db, rss_client: RSSClient, blog: Blog) -> bool:
    source = db.query(BlogSource).filter(BlogSource.id == blog.blog_source_id).first()
    if source is None:
        return False
    try:
        rss_client.get_content(source.rss_feed_link, blog.guid)
        return False
    except RSSFeedError:
        return True


def main() -> None:
    db = SessionLocal()
    rss_client = RSSClient()
    try:
        candidates = {b.id: b for b in find_missing_summary(db)}
        candidates.update({b.id: b for b in find_missing_simplify(db)})
        print(f"Checking {len(candidates)} candidate(s)...", flush=True)

        aged_out = []
        for i, blog in enumerate(candidates.values(), 1):
            if is_aged_out(db, rss_client, blog):
                aged_out.append(blog)
                print(f"  [{i}/{len(candidates)}] aged-out: '{blog.title}'", flush=True)
            else:
                print(
                    f"  [{i}/{len(candidates)}] still in feed: '{blog.title}'",
                    flush=True,
                )

        print(
            f"Found {len(aged_out)} article(s) with permanently aged-out RSS content:"
        )
        for blog in aged_out:
            print(f"  - '{blog.title}' ({blog.id})")

        for blog in aged_out:
            db.query(BlogTag).filter(BlogTag.blog_id == blog.id).delete()
            db.query(BlogPrerequisite).filter(
                BlogPrerequisite.blog_id == blog.id
            ).delete()
            db.query(Feedback).filter(Feedback.blog_id == blog.id).delete()
            db.query(Summary).filter(Summary.blog_id == blog.id).delete()
            db.query(Simplify).filter(Simplify.blog_id == blog.id).delete()
            db.query(Blog).filter(Blog.id == blog.id).delete()
            db.commit()

        print()
        print(f"Deleted {len(aged_out)} article(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
