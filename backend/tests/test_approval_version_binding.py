"""
Unit and integration tests for Improvement 3 — Stage 1: Approval Version Binding.
Verifies that:
1. Approvals can store version_id and content_hash bound to an immutable ContentVersion.
2. Existing approval records with NULL version_id/content_hash remain valid and readable.
3. The foreign key relationship approval.version correctly references ContentVersion.
4. Pydantic schema ApprovalOut properly exposes version_id and content_hash.
5. Model consistency: metadata foreign keys, mapper configuration, and no circular imports.
6. Full isolated Alembic migration lifecycle:
   - Upgrade from b2c3d4e5f6a7 to c3d4e5f6a7b8 on a disposable SQLite database.
   - Columns, FK, and index exist.
   - Existing rows preserved with NULL values.
   - Safe downgrade back to b2c3d4e5f6a7 removes columns/indexes.
   - Re-upgrade to c3d4e5f6a7b8 succeeds.
"""
import os
import hashlib
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, configure_mappers

from app.models.workspace import Workspace
from app.models.user import User
from app.models.review import ContentReview
from app.models.version import ContentVersion
from app.models.approval import Approval
from app.schemas.approval import ApprovalOut
from app.core.security import get_password_hash
from app.core.config import settings


@pytest.fixture
def binding_env(db: Session):
    """Set up workspace, users, and review for testing approval version binding."""
    ws = Workspace(name="Governance Org", org_id="ORG-GOV-001")
    db.add(ws)
    db.flush()

    author = User(name="Test Employee", email="employee@gov.com", hashed_password=get_password_hash("pass"), role="User")
    reviewer = User(name="Test Reviewer", email="reviewer@gov.com", hashed_password=get_password_hash("pass"), role="User")
    db.add_all([author, reviewer])
    db.flush()

    sample_text = "Our verified enterprise solution guarantees top security standards."
    sample_hash = hashlib.sha256(sample_text.encode("utf-8")).hexdigest()

    review = ContentReview(
        title="Spring Campaign Launch",
        content=sample_text,
        original_content=sample_text,
        content_type="marketing_copy",
        workspace_id=ws.id,
        submitted_by=author.id,
        compliance_score=92,
        status="in_review",
        audit_status="verified",
        audited_content_hash=sample_hash,
        current_version_number=1,
    )
    db.add(review)
    db.flush()

    v1 = ContentVersion(
        review_id=review.id,
        version_number=1,
        content=review.content,
        content_hash=review.audited_content_hash,
        compliance_score=92,
        status="in_review",
        audit_status="verified",
        findings_count=0,
        rule_set_version="v1.0",
        summary="Initial draft",
        change_description="Initial Submission",
        author_id=author.id,
    )
    db.add(v1)
    db.flush()

    return {
        "workspace": ws,
        "author": author,
        "reviewer": reviewer,
        "review": review,
        "version": v1,
    }


def test_new_approval_record_persists_version_and_content_hash(db: Session, binding_env):
    """Verify new approval records can store version_id and content_hash bound to ContentVersion."""
    env = binding_env
    version = env["version"]
    review = env["review"]
    author = env["author"]
    reviewer = env["reviewer"]

    approval = Approval(
        review_id=review.id,
        version_id=version.id,
        version_number=version.version_number,
        content_hash=version.content_hash,
        submitted_by=author.id,
        reviewer_id=reviewer.id,
        status="pending",
        comment="Requesting review for Version 1",
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)

    assert approval.id is not None
    assert approval.version_id == version.id
    assert approval.version_number == 1
    assert approval.content_hash == version.content_hash
    assert len(approval.content_hash) == 64

    # Verify relationship navigation
    assert approval.version is not None
    assert approval.version.id == version.id
    assert approval.version.version_number == 1
    assert approval.version.content_hash == version.content_hash


def test_existing_approval_without_version_remains_valid(db: Session, binding_env):
    """Verify legacy approval records with NULL version_id and content_hash remain valid."""
    env = binding_env
    review = env["review"]
    author = env["author"]

    legacy_approval = Approval(
        review_id=review.id,
        submitted_by=author.id,
        status="pending",
        comment="Legacy approval created before version binding",
        version_id=None,
        content_hash=None,
        version_number=None,
    )
    db.add(legacy_approval)
    db.commit()
    db.refresh(legacy_approval)

    assert legacy_approval.id is not None
    assert legacy_approval.version_id is None
    assert legacy_approval.content_hash is None
    assert legacy_approval.version_number is None
    assert legacy_approval.version is None

    # Verify updating legacy record does not fail
    legacy_approval.status = "approved"
    legacy_approval.comment = "Approved retroactively"
    db.commit()
    db.refresh(legacy_approval)
    assert legacy_approval.status == "approved"


def test_approval_foreign_key_references_correct_version(db: Session, binding_env):
    """Verify approval correctly links to specific version when multiple versions exist."""
    env = binding_env
    review = env["review"]
    author = env["author"]
    v1 = env["version"]

    v2_content = "Revised copy addressing review feedback."
    v2_hash = hashlib.sha256(v2_content.encode("utf-8")).hexdigest()
    v2 = ContentVersion(
        review_id=review.id,
        version_number=2,
        content=v2_content,
        content_hash=v2_hash,
        compliance_score=98,
        status="in_review",
        audit_status="verified",
        findings_count=0,
        author_id=author.id,
        change_description="Resolved compliance issues",
    )
    db.add(v2)
    db.flush()

    approval_v1 = Approval(
        review_id=review.id,
        version_id=v1.id,
        version_number=v1.version_number,
        content_hash=v1.content_hash,
        status="changes_requested",
    )
    approval_v2 = Approval(
        review_id=review.id,
        version_id=v2.id,
        version_number=v2.version_number,
        content_hash=v2.content_hash,
        status="pending",
    )
    db.add_all([approval_v1, approval_v2])
    db.commit()

    db.refresh(approval_v1)
    db.refresh(approval_v2)

    assert approval_v1.version_id == v1.id
    assert approval_v1.version.version_number == 1
    assert approval_v1.content_hash == v1.content_hash

    assert approval_v2.version_id == v2.id
    assert approval_v2.version.version_number == 2
    assert approval_v2.content_hash == v2_hash


def test_approval_out_schema_exposes_version_id_and_content_hash():
    """Verify ApprovalOut pydantic schema properly serializes version_id and content_hash."""
    now = datetime.now(timezone.utc)
    dummy_hash = "a" * 64

    # 1. With bound version
    approval_data = {
        "id": 101,
        "review_id": 5,
        "brand_rule_id": None,
        "submitted_by": 1,
        "reviewer_id": 2,
        "status": "pending",
        "comment": "Please approve v2",
        "version_number": 2,
        "version_id": 15,
        "content_hash": dummy_hash,
        "created_at": now,
        "updated_at": now,
    }
    approval_out = ApprovalOut.model_validate(approval_data)
    assert approval_out.id == 101
    assert approval_out.version_id == 15
    assert approval_out.version_number == 2
    assert approval_out.content_hash == dummy_hash

    # 2. Null version (backward compatibility)
    approval_legacy_data = {
        "id": 102,
        "review_id": 5,
        "brand_rule_id": None,
        "submitted_by": 1,
        "reviewer_id": None,
        "status": "approved",
        "comment": None,
        "version_number": None,
        "version_id": None,
        "content_hash": None,
        "created_at": now,
        "updated_at": now,
    }
    legacy_out = ApprovalOut.model_validate(approval_legacy_data)
    assert legacy_out.id == 102
    assert legacy_out.version_id is None
    assert legacy_out.content_hash is None
    assert legacy_out.version_number is None


def test_migration_file_structure_and_revision_chain():
    """Verify Alembic migration file exists and is cleanly chained from b2c3d4e5f6a7."""
    migration_path = Path(__file__).resolve().parent.parent / "alembic" / "versions" / "c3d4e5f6a7b8_add_approval_version_binding.py"
    assert migration_path.exists(), f"Migration file not found at {migration_path}"

    spec = importlib.util.spec_from_file_location("migration_c3d4e5f6a7b8", str(migration_path))
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    assert migration.revision == "c3d4e5f6a7b8"
    assert migration.down_revision == "b2c3d4e5f6a7"
    assert callable(migration.upgrade)
    assert callable(migration.downgrade)


def test_model_consistency_and_metadata_mapper():
    """Verify SQLAlchemy metadata contains FK, relationship resolves, and mappers configure cleanly."""
    configure_mappers()

    # Verify table column metadata
    assert "version_id" in Approval.__table__.c
    assert "content_hash" in Approval.__table__.c

    # Verify column properties
    version_id_col = Approval.__table__.c.version_id
    assert version_id_col.nullable is True
    assert version_id_col.index is True

    content_hash_col = Approval.__table__.c.content_hash
    assert content_hash_col.nullable is True
    assert content_hash_col.type.length == 64

    # Verify foreign key constraint targets content_versions.id
    fk_targets = [fk.target_fullname for fk in version_id_col.foreign_keys]
    assert "content_versions.id" in fk_targets

    # Verify relationship resolves to ContentVersion without circular imports
    rel = Approval.__mapper__.relationships["version"]
    assert rel.mapper.class_ is ContentVersion


def test_isolated_alembic_migration_lifecycle(tmp_path):
    """
    Test full lifecycle of migration c3d4e5f6a7b8 on a disposable SQLite database:
    1. Upgrade to parent revision b2c3d4e5f6a7.
    2. Insert an existing approval row (pre-migration data).
    3. Upgrade to c3d4e5f6a7b8.
    4. Confirm columns, index, and foreign key exist.
    5. Confirm existing row remains readable and new fields are NULL.
    6. Downgrade back to b2c3d4e5f6a7.
    7. Confirm new columns, index, and foreign key are removed.
    8. Confirm existing row remains intact.
    9. Upgrade again to c3d4e5f6a7b8 successfully.
    """
    from alembic.config import Config
    from alembic import command

    temp_db_file = tmp_path / "disposable_migration_test.db"
    temp_db_url = f"sqlite:///{temp_db_file.as_posix()}"

    old_url = settings.DATABASE_URL
    old_env = os.environ.get("DATABASE_URL")

    try:
        settings.DATABASE_URL = temp_db_url
        os.environ["DATABASE_URL"] = temp_db_url

        ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
        cfg = Config(str(ini_path))

        # 1. Start from parent revision b2c3d4e5f6a7
        command.upgrade(cfg, "b2c3d4e5f6a7")

        engine = create_engine(temp_db_url, connect_args={"check_same_thread": False})
        with engine.begin() as conn:
            # Insert workspace
            conn.execute(text("INSERT INTO workspaces (id, name, org_id) VALUES (1, 'Test Org', 'ORG-TEST')"))
            # Insert user
            conn.execute(text("INSERT INTO users (id, email, hashed_password, name, role) VALUES (1, 'u@t.com', 'hash', 'U', 'User')"))
            # Insert review
            conn.execute(text(
                "INSERT INTO content_reviews (id, workspace_id, title, content, original_content, content_type, status, compliance_score, audit_status, current_version_number) "
                "VALUES (1, 1, 'Rev 1', 'Sample text', 'Sample text', 'article', 'in_review', 100, 'verified', 1)"
            ))
            # Insert pre-existing approval before migration
            conn.execute(text(
                "INSERT INTO approvals (id, review_id, submitted_by, status, comment, version_number) "
                "VALUES (1, 1, 1, 'pending', 'Legacy approval before Stage 1', 1)"
            ))

        # 2. Run actual migration to c3d4e5f6a7b8
        command.upgrade(cfg, "c3d4e5f6a7b8")

        # 3. Verify columns, FK, and index exist
        insp = inspect(engine)
        col_names = [c["name"] for c in insp.get_columns("approvals")]
        assert "version_id" in col_names, "version_id column not found in approvals"
        assert "content_hash" in col_names, "content_hash column not found in approvals"

        fk_list = insp.get_foreign_keys("approvals")
        fk_found = any(fk["referred_table"] == "content_versions" and "version_id" in fk["constrained_columns"] for fk in fk_list)
        assert fk_found, "Foreign key from approvals.version_id to content_versions not found"

        indexes = [idx["name"] for idx in insp.get_indexes("approvals")]
        assert any("ix_approvals_version_id" in (idx or "") for idx in indexes), "Index on approvals.version_id not found"

        # 4. Verify existing approval rows remain readable and new fields are NULL
        with engine.connect() as conn:
            row = conn.execute(text("SELECT id, status, comment, version_number, version_id, content_hash FROM approvals WHERE id = 1")).fetchone()
            assert row is not None
            assert row[0] == 1
            assert row[1] == "pending"
            assert row[2] == "Legacy approval before Stage 1"
            assert row[3] == 1
            assert row[4] is None, f"Expected version_id to be NULL on legacy row, got {row[4]}"
            assert row[5] is None, f"Expected content_hash to be NULL on legacy row, got {row[5]}"

        # 5. Downgrade back to b2c3d4e5f6a7
        command.downgrade(cfg, "b2c3d4e5f6a7")

        insp = inspect(engine)
        downgraded_cols = [c["name"] for c in insp.get_columns("approvals")]
        assert "version_id" not in downgraded_cols, "version_id should be removed on downgrade"
        assert "content_hash" not in downgraded_cols, "content_hash should be removed on downgrade"

        downgraded_indexes = [idx["name"] for idx in insp.get_indexes("approvals")]
        assert not any("ix_approvals_version_id" in (idx or "") for idx in downgraded_indexes), "Index should be dropped on downgrade"

        # Confirm legacy row is intact after downgrade
        with engine.connect() as conn:
            row = conn.execute(text("SELECT id, status, comment, version_number FROM approvals WHERE id = 1")).fetchone()
            assert row is not None
            assert row[1] == "pending"

        # 6. Upgrade again to c3d4e5f6a7b8 successfully
        command.upgrade(cfg, "c3d4e5f6a7b8")

        insp = inspect(engine)
        reupgraded_cols = [c["name"] for c in insp.get_columns("approvals")]
        assert "version_id" in reupgraded_cols
        assert "content_hash" in reupgraded_cols

        engine.dispose()
    finally:
        settings.DATABASE_URL = old_url
        if old_env is not None:
            os.environ["DATABASE_URL"] = old_env
        else:
            os.environ.pop("DATABASE_URL", None)
