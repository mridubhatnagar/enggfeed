"""add optional name/email to feedback

Revision ID: d4e5f6a7b8c9
Revises: c2d9a4e1f3b7
Create Date: 2026-08-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2d9a4e1f3b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("feedback", sa.Column("name", sa.Text(), nullable=True))
    op.add_column("feedback", sa.Column("email", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("feedback", "email")
    op.drop_column("feedback", "name")
