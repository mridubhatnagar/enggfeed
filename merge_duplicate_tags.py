"""
One-off script — merges known singular/plural duplicate tags found by
check_tag_singular_plural.py. Repoints every blog_tag row from the duplicate
tag to the canonical tag (skipping if the blog already has the canonical tag,
to avoid a primary-key collision), then deletes the now-orphaned duplicate
Tag row.

Run:
    docker exec -it app_enggsystemfeed python merge_duplicate_tags.py
"""

import blog.models  # noqa: F401 -- registers Blog for blog_tag's FK resolution
from database import SessionLocal
from tags.models import BlogTag, Tag

# (canonical tag string, duplicate tag string to merge into it)
MERGES = [
    ("ai-agent", "ai-agents"),
    ("data-space", "data-spaces"),
]


def merge_tag(db, canonical_str: str, duplicate_str: str) -> None:
    canonical = db.query(Tag).filter(Tag.tag == canonical_str).first()
    duplicate = db.query(Tag).filter(Tag.tag == duplicate_str).first()

    if canonical is None or duplicate is None:
        print(f"  [skip] '{canonical_str}' / '{duplicate_str}' — one or both not found")
        return

    duplicate_links = db.query(BlogTag).filter(BlogTag.tag_id == duplicate.tag_id).all()
    repointed = dropped = 0
    for link in duplicate_links:
        already_has_canonical = (
            db.query(BlogTag)
            .filter(BlogTag.blog_id == link.blog_id, BlogTag.tag_id == canonical.tag_id)
            .first()
        )
        db.delete(link)
        if already_has_canonical is None:
            db.add(BlogTag(blog_id=link.blog_id, tag_id=canonical.tag_id))
            repointed += 1
        else:
            dropped += 1

    db.delete(duplicate)
    db.commit()
    print(
        f"  [merged] '{duplicate_str}' -> '{canonical_str}' "
        f"(repointed={repointed}, already_had_canonical={dropped})"
    )


def main() -> None:
    db = SessionLocal()
    try:
        for canonical_str, duplicate_str in MERGES:
            merge_tag(db, canonical_str, duplicate_str)
    finally:
        db.close()


if __name__ == "__main__":
    main()
