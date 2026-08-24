"""
One-off script to export all prerequisite content generated locally, for
applying to another environment via apply_prerequisite_content.py — avoids
paying for the same LLM calls twice across environments.

Matching is done by topic_name on the apply side, not by id, since local
and server prerequisite ids are not guaranteed to align.

Usage:
    docker exec -it app_enggsystemfeed python export_prerequisite_content.py
"""

import json

from database import SessionLocal
from prerequisites.models import Prerequisite


def main() -> None:
    db = SessionLocal()
    try:
        rows = (
            db.query(Prerequisite.topic_name, Prerequisite.content)
            .filter(Prerequisite.content.isnot(None))
            .all()
        )

        entries = [
            {"topic_name": topic_name, "content": content}
            for topic_name, content in rows
        ]

        with open("prerequisite_content_export.json", "w") as f:
            json.dump(entries, f)

        print(f"Exported {len(entries)} prerequisite(s) with content.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
