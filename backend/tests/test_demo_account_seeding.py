import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.core.security import get_password_hash, verify_password
from scripts.seed_demo_accounts import (
    DEMO_ACCOUNTS,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_ORG_ID,
    verify_database_schema,
    resolve_or_create_workspace,
    seed_or_update_accounts,
    seed_baseline_rules,
    verify_demo_accounts,
)


def test_seed_demo_accounts_lifecycle_and_idempotency(db: Session):
    """
    Test 1: Full lifecycle and idempotency.
    - Resolves/creates evaluation workspace.
    - Seeds all 3 accounts.
    - Re-executes seeder and verifies zero duplicates are created.
    """
    # First execution on fresh DB
    ws1 = resolve_or_create_workspace(db)
    assert ws1 is not None
    assert ws1.name == DEFAULT_WORKSPACE_NAME
    assert ws1.org_id == DEFAULT_ORG_ID

    seed_res = seed_or_update_accounts(db, ws1)
    assert len(seed_res) == 3
    seed_baseline_rules(db, ws1)

    # Verification must pass
    assert verify_demo_accounts(db, ws1) is True

    # Check each account in DB
    for acc in DEMO_ACCOUNTS:
        u = db.query(User).filter(User.email == acc["email"].lower()).first()
        assert u is not None
        assert u.role == acc["role"]
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == ws1.id,
                WorkspaceMember.user_id == u.id,
            )
            .first()
        )
        assert member is not None
        assert member.role == acc["role"]
        assert member.status == "approved"

    # Second execution (idempotency check)
    ws2 = resolve_or_create_workspace(db)
    assert ws2.id == ws1.id  # Same workspace reused

    seed_res_2 = seed_or_update_accounts(db, ws2)
    for email, data in seed_res_2.items():
        assert data["action"] == "UPDATED"

    # Count records: should not have duplicates
    assert db.query(Workspace).count() == 1
    assert db.query(User).count() == 3
    assert db.query(WorkspaceMember).count() == 3

    # Verification must still pass
    assert verify_demo_accounts(db, ws2) is True


def test_customer_isolation_and_unrelated_records_untouched(db: Session):
    """
    Test 2: Unrelated users and workspaces remain completely untouched.
    - Create a customer workspace and customer users.
    - Run the seeder.
    - Assert customer data is completely isolated and unmodified.
    - Assert customer workspace is NOT commandeered as the evaluation workspace.
    """
    # Setup unrelated customer organization & user
    customer_ws = Workspace(name="Real Customer Enterprise", org_id="ORG-CUST1234")
    db.add(customer_ws)
    db.commit()
    db.refresh(customer_ws)

    original_cust_hash = get_password_hash("CustomerSecret999!")
    customer_user = User(
        name="Alice RealCustomer",
        email="alice@customer-enterprise.com",
        hashed_password=original_cust_hash,
        role="Admin",
    )
    db.add(customer_user)
    db.commit()
    db.refresh(customer_user)

    customer_membership = WorkspaceMember(
        workspace_id=customer_ws.id,
        user_id=customer_user.id,
        role="Admin",
        status="approved",
    )
    db.add(customer_membership)
    db.commit()

    # Now execute the evaluation seeder
    eval_ws = resolve_or_create_workspace(db)

    # Must NOT use the customer workspace!
    assert eval_ws.id != customer_ws.id
    assert eval_ws.org_id == DEFAULT_ORG_ID
    assert eval_ws.name == DEFAULT_WORKSPACE_NAME

    seed_or_update_accounts(db, eval_ws)
    seed_baseline_rules(db, eval_ws)

    # Verify customer records remain 100% UNTOUCHED
    cust_check_ws = db.query(Workspace).filter(Workspace.id == customer_ws.id).first()
    assert cust_check_ws.name == "Real Customer Enterprise"
    assert cust_check_ws.org_id == "ORG-CUST1234"

    cust_check_user = db.query(User).filter(User.id == customer_user.id).first()
    assert cust_check_user.name == "Alice RealCustomer"
    assert cust_check_user.email == "alice@customer-enterprise.com"
    assert cust_check_user.role == "Admin"
    assert cust_check_user.hashed_password == original_cust_hash

    # Customer user must NOT be added to evaluation workspace
    assert (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == eval_ws.id,
            WorkspaceMember.user_id == customer_user.id,
        )
        .first()
        is None
    )

    # Demo users must NOT be added to customer workspace
    demo_in_cust = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.workspace_id == customer_ws.id)
        .all()
    )
    assert len(demo_in_cust) == 1
    assert demo_in_cust[0].user_id == customer_user.id


def test_conflicting_demo_user_updated_safely(db: Session):
    """
    Test 3: Handling conflicting existing user records for demo emails.
    - If a demo email exists with outdated password or wrong role/membership,
      the seeder brings it safely into compliance without breaking or duplicating.
    """
    eval_ws = resolve_or_create_workspace(db)

    # Pre-create demo user with an outdated password and unapproved Employee status instead of Admin
    outdated_pw_hash = get_password_hash("OldWrongPassword123!")
    existing_admin = User(
        name="Old Admin Name",
        email="admin_verify_rc_v2@test.com",
        hashed_password=outdated_pw_hash,
        role="User",
    )
    db.add(existing_admin)
    db.commit()
    db.refresh(existing_admin)

    stale_membership = WorkspaceMember(
        workspace_id=eval_ws.id,
        user_id=existing_admin.id,
        role="Employee",  # Stale role
        status="pending",  # Stale status
    )
    db.add(stale_membership)
    db.commit()

    # Before seed: verify password check fails with Pass123!
    assert verify_password("Pass123!", existing_admin.hashed_password) is False

    # Execute seeder
    seed_or_update_accounts(db, eval_ws)

    # Assert user credentials updated
    db.refresh(existing_admin)
    assert existing_admin.name == "Admin_Verify_Rc_V2"
    assert existing_admin.role == "Admin"
    assert verify_password("Pass123!", existing_admin.hashed_password) is True

    # Assert membership brought to approved Admin
    db.refresh(stale_membership)
    assert stale_membership.role == "Admin"
    assert stale_membership.status == "approved"

    # Verification must pass
    assert verify_demo_accounts(db, eval_ws) is True


def test_dry_run_performs_zero_database_writes(db: Session):
    """
    Test 4: Confirm --dry-run performs zero database writes.
    """
    initial_user_count = db.query(User).count()
    initial_ws_count = db.query(Workspace).count()
    initial_member_count = db.query(WorkspaceMember).count()

    ws_mock = resolve_or_create_workspace(db, dry_run=True)
    seed_or_update_accounts(db, ws_mock, dry_run=True)
    seed_baseline_rules(db, ws_mock, dry_run=True)
    db.rollback()

    assert db.query(User).count() == initial_user_count
    assert db.query(Workspace).count() == initial_ws_count
    assert db.query(WorkspaceMember).count() == initial_member_count


def test_schema_verification_rejects_missing_tables():
    """
    Test 5: Schema verification fails safely with a clear message
    when required tables or columns are missing, and executes NO DDL.
    """
    # Create an empty in-memory SQLite engine with NO tables
    empty_engine = create_engine("sqlite:///:memory:")

    with pytest.raises(RuntimeError) as exc_info:
        verify_database_schema(empty_engine)

    assert "Missing required table" in str(exc_info.value)
    assert "alembic upgrade head" in str(exc_info.value)


def test_schema_verification_rejects_missing_columns():
    """
    Test 6: Schema verification fails safely when a required column is missing.
    """
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))  # Missing email, name, etc.
        conn.execute(text("CREATE TABLE workspaces (id INTEGER PRIMARY KEY, org_id VARCHAR(32), name VARCHAR(120))"))
        conn.execute(text("CREATE TABLE workspace_members (id INTEGER PRIMARY KEY, workspace_id INT, user_id INT, role VARCHAR(50), status VARCHAR(50))"))
        conn.execute(text("CREATE TABLE brand_rules (id INTEGER PRIMARY KEY, workspace_id INT, title VARCHAR, description VARCHAR, category VARCHAR, approval_status VARCHAR)"))
        conn.commit()

    with pytest.raises(RuntimeError) as exc_info:
        verify_database_schema(engine)

    assert "missing required column" in str(exc_info.value)
    assert "alembic upgrade head" in str(exc_info.value)
