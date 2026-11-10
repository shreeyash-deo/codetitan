"""Add audit tracking to content_reviews

Revision ID: 9c8d7e6f5a4b
Revises: 7a8b9c0d1e2f
Create Date: 2026-11-11 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c8d7e6f5a4b'
down_revision: Union[str, Sequence[str], None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('content_reviews', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('audit_status', sa.String(length=50), nullable=False, server_default='verified')
        )
        batch_op.add_column(
            sa.Column('audited_content_hash', sa.String(length=64), nullable=True)
        )
        batch_op.add_column(
            sa.Column('audited_at', sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('rule_set_version', sa.String(length=100), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('content_reviews', schema=None) as batch_op:
        batch_op.drop_column('rule_set_version')
        batch_op.drop_column('findings_count')
        batch_op.drop_column('audited_at')
        batch_op.drop_column('audited_content_hash')
        batch_op.drop_column('audit_status')
