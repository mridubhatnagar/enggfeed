"""drop blog_chunk table

Revision ID: a1b2c3d4e5f6
Revises: 9770442d8622
Create Date: 2026-03-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '9770442d8622'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("blog_chunk")


def downgrade() -> None:
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
