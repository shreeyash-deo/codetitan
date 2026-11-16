"""Add version_id and content_hash to approvals for approval version binding

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-16 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility while preserving PostgreSQL support
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('version_id', sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column('content_hash', sa.String(length=64), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_approvals_version_id_content_versions',
            'content_versions',
            ['version_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index(
            op.f('ix_approvals_version_id'),
            ['version_id'],
            unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_approvals_version_id'))
        batch_op.drop_constraint('fk_approvals_version_id_content_versions', type_='foreignkey')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('version_id')
