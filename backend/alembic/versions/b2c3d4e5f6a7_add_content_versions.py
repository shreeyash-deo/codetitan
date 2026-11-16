"""Add content_versions table and version tracking to reviews, findings, and approvals

Revision ID: b2c3d4e5f6a7
Revises: 9c8d7e6f5a4b
Create Date: 2026-11-16 19:00:00.000000

"""
import hashlib
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = '9c8d7e6f5a4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create content_versions table
    op.create_table(
        'content_versions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('review_id', sa.Integer(), sa.ForeignKey('content_reviews.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('compliance_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_review'),
        sa.Column('audit_status', sa.String(length=50), nullable=False),
        sa.Column('findings_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rule_set_version', sa.String(length=100), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('change_description', sa.String(length=255), nullable=True),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('review_id', 'version_number', name='uq_content_versions_review_version')
    )
    op.create_index(op.f('ix_content_versions_review_id'), 'content_versions', ['review_id'], unique=False)
    op.create_index(op.f('ix_content_versions_author_id'), 'content_versions', ['author_id'], unique=False)

    # 2. Add current_version_number to content_reviews
    with op.batch_alter_table('content_reviews', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('current_version_number', sa.Integer(), nullable=False, server_default='1')
        )

    # 3. Add version_id to findings
    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('version_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_findings_version_id_content_versions',
            'content_versions',
            ['version_id'],
            ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_index(op.f('ix_findings_version_id'), ['version_id'], unique=False)

    # 4. Add version_number to approvals
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('version_number', sa.Integer(), nullable=True)
        )

    # 5. Backfill existing reviews
    bind = op.get_bind()
    metadata = sa.MetaData()
    content_reviews_table = sa.Table(
        'content_reviews',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('content', sa.Text()),
        sa.Column('original_content', sa.Text()),
        sa.Column('compliance_score', sa.Integer()),
        sa.Column('status', sa.String(50)),
        sa.Column('audit_status', sa.String(50)),
        sa.Column('audited_content_hash', sa.String(64)),
        sa.Column('findings_count', sa.Integer()),
        sa.Column('rule_set_version', sa.String(100)),
        sa.Column('summary', sa.Text()),
        sa.Column('submitted_by', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('current_version_number', sa.Integer()),
    )
    content_versions_table = sa.Table(
        'content_versions',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('review_id', sa.Integer()),
        sa.Column('version_number', sa.Integer()),
        sa.Column('content', sa.Text()),
        sa.Column('content_hash', sa.String(64)),
        sa.Column('compliance_score', sa.Integer()),
        sa.Column('status', sa.String(50)),
        sa.Column('audit_status', sa.String(50)),
        sa.Column('findings_count', sa.Integer()),
        sa.Column('rule_set_version', sa.String(100)),
        sa.Column('summary', sa.Text()),
        sa.Column('change_description', sa.String(255)),
        sa.Column('author_id', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True)),
    )
    findings_table = sa.Table(
        'findings',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('review_id', sa.Integer()),
        sa.Column('version_id', sa.Integer()),
    )
    approvals_table = sa.Table(
        'approvals',
        metadata,
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('review_id', sa.Integer()),
        sa.Column('version_number', sa.Integer()),
    )

    reviews_data = bind.execute(sa.select(content_reviews_table)).fetchall()
    for row in reviews_data:
        review_id = row.id
        content = row.content or ""
        original_content = row.original_content or ""
        expected_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()

        # Determine description and audit status per legacy migration semantics
        if original_content and original_content != content:
            change_desc = "Legacy Snapshot"
        else:
            change_desc = "Initial Submission"

        if row.audited_content_hash and row.audited_content_hash == expected_hash and row.audit_status in ("verified", "degraded"):
            ver_audit_status = row.audit_status
        else:
            ver_audit_status = "unverified"

        ins_res = bind.execute(
            content_versions_table.insert().values(
                review_id=review_id,
                version_number=1,
                content=content,
                content_hash=row.audited_content_hash or expected_hash,
                compliance_score=row.compliance_score if row.compliance_score is not None else 100,
                status=row.status or "in_review",
                audit_status=ver_audit_status,
                findings_count=row.findings_count or 0,
                rule_set_version=row.rule_set_version,
                summary=row.summary,
                change_description=change_desc,
                author_id=row.submitted_by,
                created_at=row.created_at or datetime.now(timezone.utc),
            )
        )
        version_1_id = ins_res.inserted_primary_key[0] if ins_res.inserted_primary_key else None
        if not version_1_id:
            # Fallback for dialects that don't return inserted_primary_key
            v_row = bind.execute(
                sa.select(content_versions_table.c.id).where(
                    content_versions_table.c.review_id == review_id,
                    content_versions_table.c.version_number == 1
                )
            ).fetchone()
            if v_row:
                version_1_id = v_row[0]

        if version_1_id:
            # Backfill existing findings for this review to version 1
            bind.execute(
                findings_table.update().where(
                    findings_table.c.review_id == review_id
                ).values(version_id=version_1_id)
            )

        # Backfill existing approvals for this review to version 1
        bind.execute(
            approvals_table.update().where(
                approvals_table.c.review_id == review_id
            ).values(version_number=1)
        )


def downgrade() -> None:
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.drop_column('version_number')

    with op.batch_alter_table('findings', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_findings_version_id'))
        batch_op.drop_constraint('fk_findings_version_id_content_versions', type_='foreignkey')
        batch_op.drop_column('version_id')

    with op.batch_alter_table('content_reviews', schema=None) as batch_op:
        batch_op.drop_column('current_version_number')

    op.drop_index(op.f('ix_content_versions_author_id'), table_name='content_versions')
    op.drop_index(op.f('ix_content_versions_review_id'), table_name='content_versions')
    op.drop_table('content_versions')
