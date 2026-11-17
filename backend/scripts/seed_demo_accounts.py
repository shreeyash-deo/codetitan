"""
BrandShield Safe Production Demo-Account Seeder
===============================================
Idempotent seeding procedure for evaluation accounts:
- Admin:    admin_verify_rc_v2@test.com / Pass123!
- Reviewer: rev_verify_rc_v2@test.com   / Pass123!
- Employee: emp_verify_rc_v2@test.com   / Pass123!

Security & Safety Architecture:
- Zero DDL: Never runs Base.metadata.create_all() or destructive DDL against production.
- Pre-flight schema validation: Verifies tables and columns exist via SQLAlchemy inspector.
- Pure Upsert: Creates or updates ONLY the 3 designated evaluation accounts.
- Customer Isolation: Never touches or assigns users to unrelated customer workspaces.
- Idempotent: Can be executed repeatedly without duplicate workspaces, users, or memberships.
- Credential Protection: Never logs or prints passwords, hashes, tokens, or DB credentials.
- Shell History Safe: Uses DATABASE_URL environment variable as primary source.
"""

import argparse
import os
import sys
from typing import Optional, Set

# Ensure backend directory is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == "scripts" else SCRIPT_DIR
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import (
    User,
    Workspace,
    WorkspaceMember,
    BrandRule,
)
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService


DEMO_ACCOUNTS = [
    {
        "role": "Admin",
        "email": "admin_verify_rc_v2@test.com",
        "password": "Pass123!",
        "name": "Admin_Verify_Rc_V2",
    },
    {
        "role": "Reviewer",
        "email": "rev_verify_rc_v2@test.com",
        "password": "Pass123!",
        "name": "Rev_Verify_Rc_V2",
    },
    {
        "role": "Employee",
        "email": "emp_verify_rc_v2@test.com",
        "password": "Pass123!",
        "name": "Emp_Verify_Rc_V2",
    },
]

DEMO_EMAILS: Set[str] = {acc["email"].lower() for acc in DEMO_ACCOUNTS}

DEFAULT_WORKSPACE_NAME = "RC Verification Org verify_rc_v2"
DEFAULT_ORG_ID = "ORG-587ABN33"

DEFAULT_RULES = [
    {
        "title": "Absolute Guarantee Prohibited",
        "description": "Content must not promise absolute or 100% guaranteed results without qualification.",
        "category": "Claims & Restrictions",
        "confidence": 0.98,
        "approval_status": "approved",
    },
    {
        "title": "Professional Terminology",
        "description": "Avoid informal slang like 'crazy secret' or 'miracle cure'.",
        "category": "Tone & Voice",
        "confidence": 0.95,
        "approval_status": "approved",
    },
]


def verify_database_schema(engine) -> None:
    """
    Verify that all required tables and columns exist before attempting to seed.
    Never executes Base.metadata.create_all() or DDL migrations in the seeding path.
    Fails safely with a clear message if tables or columns are missing.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    required_schema = {
        "users": ["id", "name", "email", "hashed_password", "role"],
        "workspaces": ["id", "org_id", "name"],
        "workspace_members": ["id", "workspace_id", "user_id", "role", "status"],
        "brand_rules": ["id", "workspace_id", "title", "description", "category", "approval_status"],
    }

    missing_tables = [tbl for tbl in required_schema if tbl not in existing_tables]
    if missing_tables:
        raise RuntimeError(
            f"Database schema verification failed: Missing required table(s): {missing_tables}. "
            f"The production database schema must be initialized via Alembic. "
            f"Please run 'alembic upgrade head' before running this seeder."
        )

    for table, required_cols in required_schema.items():
        col_names = {c["name"] for c in inspector.get_columns(table)}
        missing_cols = [c for c in required_cols if c not in col_names]
        if missing_cols:
            raise RuntimeError(
                f"Database schema verification failed: Table '{table}' is missing required column(s): {missing_cols}. "
                f"Please run 'alembic upgrade head' to apply latest migrations."
            )


def resolve_or_create_workspace(
    db: Session,
    workspace_name: Optional[str] = None,
    org_id: Optional[str] = None,
    dry_run: bool = False,
) -> Workspace:
    """
    Safely locate an existing evaluation workspace or create a dedicated one.
    Guaranteed customer-isolated:
    - Only matches explicit overrides or the designated evaluation workspace.
    - NEVER attaches demo users to unrelated customer workspaces.
    - Idempotent: will not create duplicate workspaces across multiple runs.
    """
    # 1. Explicit Org ID requested via CLI
    if org_id:
        clean_org = org_id.strip().upper()
        ws = db.query(Workspace).filter(Workspace.org_id == clean_org).first()
        if ws:
            print(f"[WORKSPACE] Found by explicit Org ID '{clean_org}': '{ws.name}' [ID: {ws.id}]")
            return ws
        raise ValueError(f"Requested workspace with Org ID '{org_id}' not found.")

    # 2. Explicit Workspace Name requested via CLI
    if workspace_name:
        clean_name = workspace_name.strip()
        ws = db.query(Workspace).filter(Workspace.name == clean_name).first()
        if ws:
            print(f"[WORKSPACE] Found by explicit name '{clean_name}': '{ws.name}' [ID: {ws.id}]")
            return ws
        raise ValueError(f"Requested workspace with name '{workspace_name}' not found.")

    # 3. Dedicated evaluation workspace by name or default org_id
    ws = (
        db.query(Workspace)
        .filter(
            (Workspace.name == DEFAULT_WORKSPACE_NAME) |
            (Workspace.org_id == DEFAULT_ORG_ID)
        )
        .first()
    )
    if ws:
        print(f"[WORKSPACE] Reusing existing evaluation workspace: '{ws.name}' ({ws.org_id}) [ID: {ws.id}]")
        return ws

    # 4. If neither exists, create a dedicated evaluation workspace
    target_org_id = DEFAULT_ORG_ID
    if db.query(Workspace).filter(Workspace.org_id == target_org_id).first():
        target_org_id = WorkspaceService.generate_org_id(db)

    target_name = DEFAULT_WORKSPACE_NAME
    if dry_run:
        print(f"[DRY-RUN] Would create dedicated evaluation workspace: '{target_name}' ({target_org_id})")
        return Workspace(id=0, name=target_name, org_id=target_org_id)

    new_ws = Workspace(name=target_name, org_id=target_org_id)
    db.add(new_ws)
    db.commit()
    db.refresh(new_ws)
    print(f"[CREATED] Dedicated Evaluation Workspace: '{new_ws.name}' ({new_ws.org_id}) [ID: {new_ws.id}]")
    return new_ws


def seed_or_update_accounts(
    db: Session,
    workspace: Workspace,
    dry_run: bool = False,
) -> dict:
    """
    Safely create or update ONLY the 3 designated evaluation accounts.
    Never modifies unrelated users or customer data.
    """
    results = {}
    for acc in DEMO_ACCOUNTS:
        email = acc["email"].lower()
        role = acc["role"]
        name = acc["name"]
        password = acc["password"]

        # Safety assertion: Only designated demo emails can ever be processed
        if email not in DEMO_EMAILS:
            raise RuntimeError(f"Safety violation: Attempted to process non-demo email '{email}'")

        user = db.query(User).filter(User.email == email).first()
        action_user = "EXISTS"
        if not user:
            if dry_run:
                print(f"[DRY-RUN] Would create evaluation user: {email} (role: {role})")
                user = User(id=0, name=name, email=email, role=role)
                action_user = "WOULD_CREATE"
            else:
                user = User(
                    name=name,
                    email=email,
                    hashed_password=get_password_hash(password),
                    role=role,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                action_user = "CREATED"
                print(f"[CREATED] Evaluation user: {email} [ID: {user.id}]")
        else:
            if not dry_run:
                user.hashed_password = get_password_hash(password)
                user.name = name
                user.role = role
                db.commit()
                db.refresh(user)
                action_user = "UPDATED"
                print(f"[UPDATED] Evaluation credentials refreshed: {email} [ID: {user.id}]")
            else:
                action_user = "WOULD_UPDATE"
                print(f"[DRY-RUN] Would refresh credentials for evaluation user: {email}")

        if not dry_run and workspace.id:
            membership = (
                db.query(WorkspaceMember)
                .filter(
                    WorkspaceMember.workspace_id == workspace.id,
                    WorkspaceMember.user_id == user.id,
                )
                .first()
            )
            if not membership:
                membership = WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role=role,
                    status="approved",
                )
                db.add(membership)
                db.commit()
                db.refresh(membership)
                print(f"[ASSIGNED] Membership: {email} -> {workspace.name} as {role} (approved)")
            else:
                if membership.role != role or membership.status != "approved":
                    membership.role = role
                    membership.status = "approved"
                    db.commit()
                    db.refresh(membership)
                    print(f"[UPDATED] Membership: {email} -> {workspace.name} updated to {role} (approved)")
                else:
                    print(f"[UNCHANGED] Membership: {email} -> {workspace.name} already {role} (approved)")

        results[email] = {
            "user": user,
            "role": role,
            "action": action_user,
        }

    return results


def seed_baseline_rules(
    db: Session,
    workspace: Workspace,
    dry_run: bool = False,
):
    """
    Ensure evaluation workspace has basic approved brand rules so
    content scans and reviews function realistically out-of-the-box.
    """
    if dry_run or not workspace.id:
        return

    for rule_def in DEFAULT_RULES:
        existing = (
            db.query(BrandRule)
            .filter(
                BrandRule.workspace_id == workspace.id,
                BrandRule.title == rule_def["title"],
            )
            .first()
        )
        if not existing:
            new_rule = BrandRule(
                workspace_id=workspace.id,
                title=rule_def["title"],
                description=rule_def["description"],
                category=rule_def["category"],
                confidence=rule_def["confidence"],
                approval_status=rule_def["approval_status"],
            )
            db.add(new_rule)
            db.commit()
            print(f"[RULE CREATED] '{new_rule.title}' in workspace '{workspace.name}'")


def verify_demo_accounts(db: Session, workspace: Workspace) -> bool:
    """
    Verify each account against:
    1. Direct password verification (verify_password)
    2. AuthService.authenticate (the exact login endpoint logic)
    3. Workspace membership role and approved status
    4. list_workspaces_for_user inclusion
    Does NOT print hashes, passwords, or sensitive tokens.
    """
    print("\n" + "=" * 75)
    print("DEMO ACCOUNTS VERIFICATION AUDIT")
    print("=" * 75)
    all_passed = True

    for acc in DEMO_ACCOUNTS:
        email = acc["email"].lower()
        expected_role = acc["role"]
        password = acc["password"]

        # 1. User existence
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"[FAIL] {email}: User record does not exist in database!")
            all_passed = False
            continue

        # 2. Password check
        pw_ok = verify_password(password, user.hashed_password)
        if not pw_ok:
            print(f"[FAIL] {email}: Password hash check failed!")
            all_passed = False
            continue

        # 3. AuthService.authenticate (identical to /api/v1/auth/login)
        auth_user = AuthService.authenticate(db, email, password)
        if not auth_user or auth_user.id != user.id:
            print(f"[FAIL] {email}: AuthService.authenticate failed!")
            all_passed = False
            continue

        # 4. Workspace membership
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace.id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not membership:
            print(f"[FAIL] {email}: No membership found in workspace '{workspace.name}'!")
            all_passed = False
            continue

        if membership.status != "approved":
            print(f"[FAIL] {email}: Membership status is '{membership.status}' (expected 'approved')!")
            all_passed = False
            continue

        if membership.role != expected_role:
            print(f"[FAIL] {email}: Membership role is '{membership.role}' (expected '{expected_role}')!")
            all_passed = False
            continue

        # 5. List accessible workspaces
        accessible_ws = WorkspaceService.list_workspaces_for_user(db, user)
        if not any(w.id == workspace.id for w in accessible_ws):
            print(f"[FAIL] {email}: Workspace '{workspace.name}' not returned in list_workspaces_for_user!")
            all_passed = False
            continue

        print(
            f"[PASS] {email:<28} | Role: {membership.role:<8} | "
            f"Status: {membership.status:<8} | Auth: VERIFIED"
        )

    print("=" * 75)
    if all_passed:
        print("[SUCCESS] All 3 demo accounts verified and ready for evaluation!")
    else:
        print("[ERROR] One or more verification checks failed.")
    print("=" * 75)
    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="BrandShield Safe Idempotent Demo-Account Seeder",
        epilog="Security Note: In production (e.g. Render Shell), leave DATABASE_URL set in the environment. Do not pass sensitive connection strings as command-line arguments to avoid leaking them into shell history."
    )
    parser.add_argument(
        "--db-url",
        dest="db_url",
        default=None,
        help="Optional database URL override (prefer setting DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--workspace-name",
        dest="workspace_name",
        default=None,
        help="Optional evaluation workspace name override",
    )
    parser.add_argument(
        "--org-id",
        dest="org_id",
        default=None,
        help="Optional evaluation Organisation ID override (e.g. ORG-XXXXXXXX)",
    )
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Simulate operations without making changes to the database",
    )
    parser.add_argument(
        "--verify-only",
        dest="verify_only",
        action="store_true",
        help="Verify accounts without modifying database records",
    )
    args = parser.parse_args()

    # Determine database connection safely
    if args.db_url:
        print("[SECURITY NOTICE] Database URL provided via command-line argument.")
        print("                  In production environments, prefer setting DATABASE_URL environment variable.")
        target_db_url = settings.normalize_database_url_input(args.db_url)
    else:
        target_db_url = settings.normalized_database_url

    connect_args = {}
    if target_db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(target_db_url, connect_args=connect_args, pool_pre_ping=True)

    # Pre-flight schema validation: strictly verifies tables and columns, NO create_all()
    try:
        verify_database_schema(engine)
    except RuntimeError as schema_err:
        print(f"\n[SCHEMA ERROR] {schema_err}", file=sys.stderr)
        sys.exit(1)

    SessionClass = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionClass()

    print("=" * 75)
    print("BRANDSHIELD PRODUCTION EVALUATION SEEDER")
    print(f"Database dialect: {engine.dialect.name}")
    print(f"Safe DB Info:     {settings.safe_database_info if not args.db_url else 'masked-target-url'}")
    print("=" * 75)

    try:
        if args.verify_only:
            # Verification-only mode: perform zero writes
            ws = (
                db.query(Workspace)
                .filter(
                    (Workspace.name == (args.workspace_name or DEFAULT_WORKSPACE_NAME)) |
                    (Workspace.org_id == (args.org_id or DEFAULT_ORG_ID))
                )
                .first()
            )
            if not ws:
                print(f"[FAIL] Evaluation workspace not found in database.")
                sys.exit(1)
            success = verify_demo_accounts(db, ws)
            sys.exit(0 if success else 1)

        ws = resolve_or_create_workspace(
            db,
            workspace_name=args.workspace_name,
            org_id=args.org_id,
            dry_run=args.dry_run,
        )

        print("\nSeeding / refreshing demo accounts...")
        seed_or_update_accounts(db, ws, dry_run=args.dry_run)
        seed_baseline_rules(db, ws, dry_run=args.dry_run)

        # Verification step
        if not args.dry_run:
            success = verify_demo_accounts(db, ws)
            sys.exit(0 if success else 1)
        else:
            db.rollback()
            print("\n[DRY-RUN] Simulation complete. Zero database mutations committed.")
            sys.exit(0)

    except Exception as e:
        print(f"\n[FATAL ERROR] Seeding aborted: {e}", file=sys.stderr)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
