"""Add org_id to workspaces, migrate Editor to Employee, and add uq_workspace_user

Revision ID: 4d8f1e2a9b3c
Revises: 2b1fcd7a6a3b
Create Date: 2026-11-10 17:00:00.000000

"""
from typing import Sequence, Union
import secrets
import string

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d8f1e2a9b3c'
down_revision: Union[str, Sequence[str], None] = '2b1fcd7a6a3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def generate_unique_org_id(existing_ids: set) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        org_id = f"ORG-{code}"
        if org_id not in existing_ids:
            existing_ids.add(org_id)
            return org_id


def upgrade() -> None:
    # 1. Add org_id as nullable first
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('org_id', sa.String(length=32), nullable=True))

    # 2. Backfill existing workspaces with cryptographically secure unique org_id
    connection = op.get_bind()
    workspaces = connection.execute(sa.text("SELECT id FROM workspaces")).fetchall()
    existing_org_ids = set()

    for ws in workspaces:
        ws_id = ws[0]
        org_id = generate_unique_org_id(existing_org_ids)
        connection.execute(
            sa.text("UPDATE workspaces SET org_id = :org_id WHERE id = :id"),
            {"org_id": org_id, "id": ws_id},
        )

    # 3. Alter org_id to NOT NULL and create unique index
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.alter_column('org_id', existing_type=sa.String(length=32), nullable=False)
        batch_op.create_index(batch_op.f('ix_workspaces_org_id'), ['org_id'], unique=True)

    # 4. Migrate existing Editor memberships to Employee
    connection.execute(
        sa.text("UPDATE workspace_members SET role = 'Employee' WHERE role = 'Editor'")
    )

    # 5. Add unique constraint on (workspace_id, user_id)
    with op.batch_alter_table('workspace_members', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_workspace_user', ['workspace_id', 'user_id'])


def downgrade() -> None:
    with op.batch_alter_table('workspace_members', schema=None) as batch_op:
        batch_op.drop_constraint('uq_workspace_user', type_='unique')

    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE workspace_members SET role = 'Editor' WHERE role = 'Employee'")
    )

    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspaces_org_id'))
        batch_op.drop_column('org_id')
