"""drop allowed_users table

Revision ID: 9da7f10dbd4f
Revises: bb8590add1d0
Create Date: 2026-04-03 04:42:43.597625

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9da7f10dbd4f'
down_revision: Union[str, Sequence[str], None] = 'bb8590add1d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('allowed_users')


def downgrade() -> None:
    op.create_table(
        'allowed_users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
