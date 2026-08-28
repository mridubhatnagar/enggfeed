"""
One-off diagnostic script — lists existing tags that look like singular/plural
duplicates of each other (e.g. 'ai-agent' vs 'ai-agents'), based on a simple
keyword normalization (lowercase, strip a trailing 's'), not embedding
similarity. Read-only: reports candidates for manual review, does not merge
anything.

Run:
    docker exec -it app_enggsystemfeed python check_tag_singular_plural.py
"""

from collections import defaultdict

from database import SessionLocal
from tags.models import BlogTag, Tag


def normalize(tag: str) -> str:
    tag = tag.strip().lower()
    if len(tag) > 1 and tag.endswith("s") and not tag.endswith("ss"):
        return tag[:-1]
    return tag


def main() -> None:
    db = SessionLocal()
    try:
        tags = db.query(Tag).all()
        groups: dict[str, list[Tag]] = defaultdict(list)
        for tag in tags:
            groups[normalize(tag.tag)].append(tag)

        candidates = {k: v for k, v in groups.items() if len(v) > 1}

        if not candidates:
            print("No singular/plural tag duplicates found.")
            return

        print(f"Found {len(candidates)} candidate duplicate group(s):\n")
        for norm_key, group in candidates.items():
            print(f"  '{norm_key}':")
            for tag in group:
                usage = db.query(BlogTag).filter(BlogTag.tag_id == tag.tag_id).count()
                print(
                    f"    - '{tag.tag}' (tag_id={tag.tag_id}, used on {usage} blog(s))"
                )
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
