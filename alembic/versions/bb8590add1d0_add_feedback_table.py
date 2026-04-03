"""add feedback table

Revision ID: bb8590add1d0
Revises: a1b2c3d4e5f6
Create Date: 2026-04-03 03:36:52.563531

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'bb8590add1d0'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_foreign_key('feedback_blog_id_fkey', 'feedback', 'blog', ['blog_id'], ['id'])
    op.create_foreign_key('feedback_user_id_fkey', 'feedback', 'user', ['user_id'], ['user_id'])


def downgrade() -> None:
    op.drop_constraint('feedback_user_id_fkey', 'feedback', type_='foreignkey')
    op.drop_constraint('feedback_blog_id_fkey', 'feedback', type_='foreignkey')
