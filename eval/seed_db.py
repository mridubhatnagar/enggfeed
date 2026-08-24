"""
One-off script to embed and insert seed tags and prerequisites into the DB.
Run this before the first ingest:
    docker exec -it enggsystemfeed-app-1 python eval/seed_db.py
"""

import json
import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from ingest.embedder import Embedder
from tags.models import Tag
from prerequisites.models import Prerequisite

SEED_TAGS_PATH = os.path.join(os.path.dirname(__file__), "seed_tags.json")
SEED_PREREQS_PATH = os.path.join(os.path.dirname(__file__), "seed_prerequisites.json")


def seed_tags(db, embedder: Embedder) -> None:
    with open(SEED_TAGS_PATH) as f:
        tags = json.load(f)

    existing = {row.tag for row in db.query(Tag).all()}
    inserted = 0

    for tag_name in tags:
        if tag_name in existing:
            print(f"  [skip] tag already exists: {tag_name}")
            continue
        embedding = embedder.embed(tag_name)
        row = Tag(
            tag_id=uuid.uuid4(),
            created_at=datetime.now(),
            tag=tag_name,
            embedding=embedding,
        )
        db.add(row)
        existing.add(tag_name)
        inserted += 1
        print(f"  [insert] tag: {tag_name}")

    db.commit()
    print(f"\nTags: {inserted} inserted, {len(tags) - inserted} skipped.\n")


def seed_prerequisites(db, embedder: Embedder) -> None:
    with open(SEED_PREREQS_PATH) as f:
        prereqs = json.load(f)

    existing = {row.topic_name for row in db.query(Prerequisite).all()}
    inserted = 0

    for topic_name in prereqs:
        if topic_name in existing:
            print(f"  [skip] prerequisite already exists: {topic_name}")
            continue
        embedding = embedder.embed(topic_name)
        row = Prerequisite(
            id=uuid.uuid4(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            topic_name=topic_name,
            embedding=embedding,
        )
        db.add(row)
        existing.add(topic_name)
        inserted += 1
        print(f"  [insert] prerequisite: {topic_name}")

    db.commit()
    print(f"\nPrerequisites: {inserted} inserted, {len(prereqs) - inserted} skipped.\n")


if __name__ == "__main__":
    db = SessionLocal()
    embedder = Embedder()
    try:
        print("=== Seeding tags ===")
        seed_tags(db, embedder)
        print("=== Seeding prerequisites ===")
        seed_prerequisites(db, embedder)
        print("Done.")
    finally:
        db.close()
