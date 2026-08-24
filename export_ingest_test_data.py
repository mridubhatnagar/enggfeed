"""One-off script to export the blog data created by the local BackgroundTasks
test ingest run (2026-08-23, ~14:03 to ~15:02) for syncing to the server.

Exports, per new blog: the blog row itself, its source name, tags (name +
embedding), prerequisites (topic_name + content + embedding), summary,
simplify, and llm_usage rows. Also records blog_source names that were
removed locally (e.g. Fly.io) so the apply script can remove them on the
server too, if safe to do so there.

Matching is done by natural key (guid for blog, tag name, topic_name) on
the apply side, not by raw id copy — local and server tag/prerequisite ids
are not guaranteed to line up since both environments normalize
independently.

Usage:
    docker exec -it app_enggsystemfeed python export_ingest_test_data.py
"""

import json

from database import SessionLocal

# Start-of-run timestamp for the local test ingest — see conversation notes.
RUN_STARTED_AT = "2026-08-23 14:03:00"
REMOVED_SOURCES = ["Fly.io"]


def _round_embedding(embedding) -> list[float]:
    # Raw SQL (sa.text) returns pgvector columns as their text form, e.g.
    # "[0.012,-0.034,...]" — not a Python list. Parse before rounding.
    # Full double precision is unnecessary for cosine similarity matching —
    # 6 decimals keeps plenty of precision while cutting export size sharply.
    if isinstance(embedding, str):
        embedding = embedding.strip("[]").split(",")
    return [round(float(x), 6) for x in embedding]


def main() -> None:
    db = SessionLocal()
    try:
        import sqlalchemy as sa

        blogs = db.execute(
            sa.text(
                "SELECT id, guid, link, title, thumbnail, word_count, "
                "published_at, created_at, blog_source_id "
                "FROM blog WHERE created_at >= :threshold ORDER BY created_at"
            ),
            {"threshold": RUN_STARTED_AT},
        ).fetchall()

        export = {"removed_sources": REMOVED_SOURCES, "blogs": []}

        for b in blogs:
            blog_id = b.id
            source = db.execute(
                sa.text("SELECT source FROM blog_source WHERE id = :id"),
                {"id": b.blog_source_id},
            ).scalar()

            tags = db.execute(
                sa.text(
                    "SELECT t.tag, t.embedding FROM tag t "
                    "JOIN blog_tag bt ON bt.tag_id = t.tag_id "
                    "WHERE bt.blog_id = :bid"
                ),
                {"bid": blog_id},
            ).fetchall()

            prereqs = db.execute(
                sa.text(
                    "SELECT p.topic_name, p.content, p.embedding FROM prerequisite p "
                    "JOIN blog_prerequisite bp ON bp.prerequisite_id = p.id "
                    "WHERE bp.blog_id = :bid"
                ),
                {"bid": blog_id},
            ).fetchall()

            summary = db.execute(
                sa.text("SELECT content FROM summary WHERE blog_id = :bid"),
                {"bid": blog_id},
            ).first()

            simplify = db.execute(
                sa.text("SELECT simplify FROM simplify WHERE blog_id = :bid"),
                {"bid": blog_id},
            ).first()

            usage_rows = db.execute(
                sa.text(
                    "SELECT call_type, provider, model, input_tokens, "
                    "output_tokens, total_tokens, cost_usd, created_at "
                    "FROM llm_usage WHERE blog_id = :bid"
                ),
                {"bid": blog_id},
            ).fetchall()

            export["blogs"].append(
                {
                    "guid": b.guid,
                    "link": b.link,
                    "title": b.title,
                    "thumbnail": b.thumbnail,
                    "word_count": b.word_count,
                    "published_at": (
                        b.published_at.isoformat() if b.published_at else None
                    ),
                    "created_at": b.created_at.isoformat(),
                    "source_name": source,
                    "tags": [
                        {"tag": t.tag, "embedding": _round_embedding(t.embedding)}
                        for t in tags
                    ],
                    "prerequisites": [
                        {
                            "topic_name": p.topic_name,
                            "content": p.content,
                            "embedding": _round_embedding(p.embedding),
                        }
                        for p in prereqs
                    ],
                    "summary": dict(summary._mapping) if summary else None,
                    "simplify": dict(simplify._mapping) if simplify else None,
                    "llm_usage": [
                        {
                            "call_type": u.call_type,
                            "provider": u.provider,
                            "model": u.model,
                            "input_tokens": u.input_tokens,
                            "output_tokens": u.output_tokens,
                            "total_tokens": u.total_tokens,
                            "cost_usd": str(u.cost_usd),
                            "created_at": u.created_at.isoformat(),
                        }
                        for u in usage_rows
                    ],
                }
            )

        with open("ingest_test_data_export.json", "w") as f:
            json.dump(export, f)

        print(f"Exported {len(export['blogs'])} blog(s).")
        print(f"Removed sources to apply: {REMOVED_SOURCES}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
