"""drop auth (user table, feedback.user_id)

Revision ID: c2d9a4e1f3b7
Revises: 9da7f10dbd4f
Create Date: 2026-08-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d9a4e1f3b7"
down_revision: Union[str, Sequence[str], None] = "9da7f10dbd4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_feedback_user_blog_type", "feedback", type_="unique")
    op.drop_constraint("feedback_user_id_fkey", "feedback", type_="foreignkey")
    op.drop_column("feedback", "user_id")
    op.drop_table("user")


def downgrade() -> None:
    op.create_table(
        "user",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("google_auth_id", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("profile_url", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.add_column("feedback", sa.Column("user_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "feedback_user_id_fkey", "feedback", "user", ["user_id"], ["user_id"]
    )
    op.create_unique_constraint(
        "uq_feedback_user_blog_type", "feedback", ["user_id", "blog_id", "type"]
    )
