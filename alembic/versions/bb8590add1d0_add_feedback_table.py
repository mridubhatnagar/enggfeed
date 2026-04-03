"""add feedback table

Revision ID: bb8590add1d0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-03 03:36:52.563531

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bb8590add1d0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("blog_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["blog_id"], ["blog.id"], name="feedback_blog_id_fkey"),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], name="feedback_user_id_fkey"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "blog_id", "type", name="uq_feedback_user_blog_type"),
    )


def downgrade() -> None:
    op.drop_table("feedback")
