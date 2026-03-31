"""initial

Revision ID: 9770442d8622
Revises:
Create Date: 2026-03-29 15:13:25.273452

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '9770442d8622'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension first.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. user
    op.create_table(
        "user",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("google_auth_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # 2. allowed_users
    op.create_table(
        "allowed_users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. blog_source
    op.create_table(
        "blog_source",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("rss_feed_link", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. blog (depends on blog_source)
    op.create_table(
        "blog",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("guid", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("thumbnail", sa.Text(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("blog_source_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["blog_source_id"], ["blog_source.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guid"),
    )

    # 5. blog_chunk (depends on blog)
    op.create_table(
        "blog_chunk",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("blog_id", sa.UUID(), nullable=True),
        sa.Column("chunk_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["blog_id"], ["blog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. summary (depends on blog)
    op.create_table(
        "summary",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("blog_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["blog_id"], ["blog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. simplify (depends on blog)
    op.create_table(
        "simplify",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("blog_id", sa.UUID(), nullable=True),
        sa.Column("simplify", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["blog_id"], ["blog.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # 8. prerequisite (no FK dependencies)
    op.create_table(
        "prerequisite",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("topic_name", sa.Text(), nullable=False),
        sa.Column("content", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_name"),
    )

    # 9. blog_prerequisite (depends on blog and prerequisite)
    op.create_table(
        "blog_prerequisite",
        sa.Column("blog_id", sa.UUID(), nullable=False),
        sa.Column("prerequisite_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["blog_id"], ["blog.id"]),
        sa.ForeignKeyConstraint(["prerequisite_id"], ["prerequisite.id"]),
        sa.PrimaryKeyConstraint("blog_id", "prerequisite_id"),
    )

    # 10. tag (no FK dependencies)
    op.create_table(
        "tag",
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("tag", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.PrimaryKeyConstraint("tag_id"),
        sa.UniqueConstraint("tag"),
    )

    # 11. blog_tag (depends on blog and tag)
    op.create_table(
        "blog_tag",
        sa.Column("blog_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["blog_id"], ["blog.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.tag_id"]),
        sa.PrimaryKeyConstraint("blog_id", "tag_id"),
    )


def downgrade() -> None:
    op.drop_table("blog_tag")
    op.drop_table("tag")
    op.drop_table("blog_prerequisite")
    op.drop_table("prerequisite")
    op.drop_table("simplify")
    op.drop_table("summary")
    op.drop_table("blog")
    op.drop_table("blog_source")
    op.drop_table("allowed_users")
    op.drop_table("user")
    op.execute("DROP EXTENSION IF EXISTS vector")
