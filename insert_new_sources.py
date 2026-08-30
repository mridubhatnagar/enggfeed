"""
One-off script — inserts the 5 newly-evaluated sources into blog_source,
name-checked so it's safe to re-run. Do NOT use eval/seed_blog_source.sql's
full INSERT for this — its ON CONFLICT DO NOTHING is keyed on `id` (a fresh
random UUID each run), and `source` has no unique constraint, so re-running
the full seed file would duplicate every existing source.

Run:
    docker exec -it app_enggsystemfeed python insert_new_sources.py
"""

import uuid

from blog.models import BlogSource
from database import SessionLocal

NEW_SOURCES = [
    ("Medium Engineering", "https://medium.engineering/feed"),
    ("ByteByteGo", "https://blog.bytebytego.com/feed"),
    ("Julia Evans", "https://jvns.ca/atom.xml"),
    ("Grab", "https://engineering.grab.com/feed.xml"),
    ("Pinterest", "https://medium.com/feed/pinterest-engineering"),
]


def main() -> None:
    db = SessionLocal()
    try:
        for name, link in NEW_SOURCES:
            existing = db.query(BlogSource).filter(BlogSource.source == name).first()
            if existing:
                print(f"  [skip] '{name}' already exists")
                continue
            db.add(BlogSource(id=uuid.uuid4(), source=name, rss_feed_link=link))
            db.commit()
            print(f"  [inserted] '{name}'")
    finally:
        db.close()


if __name__ == "__main__":
    main()
