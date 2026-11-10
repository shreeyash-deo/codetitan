"""Add status to workspace_members

Revision ID: 7a8b9c0d1e2f
Revises: 4d8f1e2a9b3c
Create Date: 2026-11-10 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = '4d8f1e2a9b3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('workspace_members', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('status', sa.String(length=50), nullable=False, server_default='approved')
        )


def downgrade() -> None:
    with op.batch_alter_table('workspace_members', schema=None) as batch_op:
        batch_op.drop_column('status')
