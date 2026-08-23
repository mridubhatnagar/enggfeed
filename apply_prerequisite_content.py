"""
One-off script to apply prerequisite content exported from another
environment (see backfill_prerequisites.py + the export step in the
matching session notes). Updates existing rows by topic_name only —
never inserts new prerequisites, since topic_name is the shared identity
across environments but ids/embeddings are not guaranteed to match.

Usage:
    docker exec -it app_enggsystemfeed python apply_prerequisite_content.py prerequisite_content_export.json
"""

import json
import sys

from database import SessionLocal
from prerequisites.dao import PrerequisiteDAO
from prerequisites.service import PrerequisiteService


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python apply_prerequisite_content.py <export.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        entries = json.load(f)

    db = SessionLocal()
    service = PrerequisiteService(PrerequisiteDAO(db))
    try:
        updated = skipped = 0
        for i, entry in enumerate(entries, 1):
            existing = service.get_prerequisite_by_topic_name(
                entry["topic_name"], use_cache=False
            )
            if existing is None:
                print(
                    f"  [{i}/{len(entries)}] skip (not found): '{entry['topic_name']}'"
                )
                skipped += 1
                continue
            service.update_prerequisite(entry["topic_name"], entry["content"])
            print(f"  [{i}/{len(entries)}] updated: '{entry['topic_name']}'")
            updated += 1

        print()
        print(f"updated={updated} skipped={skipped}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
