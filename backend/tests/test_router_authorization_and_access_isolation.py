"""
Security and isolation test suite for Improvement 3 — Stage 3:
Router Authorization & Access Isolation.

Tests all 12 required authorization and governance isolation scenarios:
1. Employee retrieves own approval successfully.
2. Employee cannot retrieve another employee's approval in the same workspace.
3. Employee cannot retrieve approval from another workspace.
4. Reviewer retrieves approvals in an authorized workspace.
5. Reviewer cannot retrieve approvals in an unauthorized workspace.
6. Reviewer cannot decide an approval outside their workspace.
7. Admin retains authorized workspace-wide access.
8. Admin cannot access unrelated workspaces.
9. Compatibility endpoints enforce the same access restrictions.
10. Revoked workspace membership prevents further access.
11. Superseded tickets remain readable as history but cannot be acted upon.
12. Employees cannot perform reviewer/admin decision actions.
"""
import hashlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.user import User
from app.models.review import ContentReview
from app.models.version import ContentVersion
from app.models.approval import Approval
from app.models.rule import BrandRule
from app.core.security import get_password_hash, create_access_token
from app.services.review_service import review_service
from app.services.approval_service import approval_service


def _auth_headers(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_isolation_env(db: Session):
    """
    Sets up two isolated workspaces (WS1, WS2) with distinct admins, reviewers,
    and employees, along with immutable reviews, versions, and approval tickets.
    """
    # 1. Create Workspaces
    ws1 = Workspace(name="Secure Org 1", org_id="ORG-SEC-001")
    ws2 = Workspace(name="Secure Org 2", org_id="ORG-SEC-002")
    db.add_all([ws1, ws2])
    db.flush()

    # 2. Create Users
    # WS1 Users
    admin1 = User(name="Admin One", email="admin1@sec.com", hashed_password=get_password_hash("pass"), role="User")
    reviewer1 = User(name="Reviewer One", email="reviewer1@sec.com", hashed_password=get_password_hash("pass"), role="User")
    employee1a = User(name="Emp 1A", email="emp1a@sec.com", hashed_password=get_password_hash("pass"), role="User")
    employee1b = User(name="Emp 1B", email="emp1b@sec.com", hashed_password=get_password_hash("pass"), role="User")
    revoked1 = User(name="Revoked User", email="revoked@sec.com", hashed_password=get_password_hash("pass"), role="User")

    # WS2 Users
    admin2 = User(name="Admin Two", email="admin2@sec.com", hashed_password=get_password_hash("pass"), role="User")
    reviewer2 = User(name="Reviewer Two", email="reviewer2@sec.com", hashed_password=get_password_hash("pass"), role="User")
    employee2 = User(name="Emp Two", email="emp2@sec.com", hashed_password=get_password_hash("pass"), role="User")

    db.add_all([admin1, reviewer1, employee1a, employee1b, revoked1, admin2, reviewer2, employee2])
    db.flush()

    # 3. Create Workspace Memberships
    members = [
        WorkspaceMember(workspace_id=ws1.id, user_id=admin1.id, role="Admin", status="approved"),
        WorkspaceMember(workspace_id=ws1.id, user_id=reviewer1.id, role="Reviewer", status="approved"),
        WorkspaceMember(workspace_id=ws1.id, user_id=employee1a.id, role="Employee", status="approved"),
        WorkspaceMember(workspace_id=ws1.id, user_id=employee1b.id, role="Employee", status="approved"),
        WorkspaceMember(workspace_id=ws1.id, user_id=revoked1.id, role="Reviewer", status="revoked"),
        WorkspaceMember(workspace_id=ws2.id, user_id=admin2.id, role="Admin", status="approved"),
        WorkspaceMember(workspace_id=ws2.id, user_id=reviewer2.id, role="Reviewer", status="approved"),
        WorkspaceMember(workspace_id=ws2.id, user_id=employee2.id, role="Employee", status="approved"),
    ]
    db.add_all(members)
    db.flush()

    rule1 = BrandRule(
        workspace_id=ws1.id,
        category="Claims & Performance",
        title="Prohibit Unsubstantiated Claims",
        description="Never guarantee 100% returns.",
        confidence=0.95,
        approval_status="approved",
    )
    rule2 = BrandRule(
        workspace_id=ws2.id,
        category="Claims & Performance",
        title="Prohibit Unsubstantiated Claims",
        description="Never guarantee 100% returns.",
        confidence=0.95,
        approval_status="approved",
    )
    db.add_all([rule1, rule2])
    db.flush()

    # 4. Helper to create review + version + approval ticket
    def create_content_and_approval(workspace_id: int, author: User, title: str, text: str):
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        review = ContentReview(
            workspace_id=workspace_id,
            submitted_by=author.id,
            title=title,
            content=text,
            original_content=text,
            content_type="article",
            status="pending",
            compliance_score=100,
            audit_status="verified",
            audited_content_hash=content_hash,
            current_version_number=1,
        )
        db.add(review)
        db.flush()

        version = ContentVersion(
            review_id=review.id,
            version_number=1,
            content=text,
            content_hash=content_hash,
            compliance_score=100,
            status="pending",
            audit_status="verified",
            findings_count=0,
            summary="Clean compliant copy",
            change_description="Initial Submission",
            author_id=author.id,
        )
        db.add(version)
        db.flush()

        approval = Approval(
            review_id=review.id,
            brand_rule_id=None,
            submitted_by=author.id,
            reviewer_id=None,
            status="pending",
            version_id=version.id,
            version_number=1,
            content_hash=content_hash,
            comment=f"Initial submission for {title}",
        )
        db.add(approval)
        db.flush()
        return review, version, approval

    review1a, v1a, approval1a = create_content_and_approval(
        ws1.id, employee1a, "Emp 1A Article", "Fully compliant copy for employee 1A."
    )
    review1b, v1b, approval1b = create_content_and_approval(
        ws1.id, employee1b, "Emp 1B Article", "Fully compliant copy for employee 1B."
    )
    review2, v2, approval2 = create_content_and_approval(
        ws2.id, employee2, "Org 2 Article", "Fully compliant copy for organisation 2."
    )

    db.commit()

    return {
        "ws1": ws1,
        "ws2": ws2,
        "admin1": admin1,
        "reviewer1": reviewer1,
        "employee1a": employee1a,
        "employee1b": employee1b,
        "revoked1": revoked1,
        "admin2": admin2,
        "reviewer2": reviewer2,
        "employee2": employee2,
        "review1a": review1a,
        "approval1a": approval1a,
        "review1b": review1b,
        "approval1b": approval1b,
        "review2": review2,
        "approval2": approval2,
    }


# ============================================================================
# 1. Employee retrieves own approval successfully
# ============================================================================
def test_01_employee_retrieves_own_approval_successfully(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["employee1a"])
    appr_id = env["approval1a"].id

    resp = client.get(f"/api/approvals/{appr_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == appr_id
    assert data["submitted_by"] == env["employee1a"].id
    assert data["status"] == "pending"
    assert data["version_number"] == 1


# ============================================================================
# 2. Employee cannot retrieve another employee's approval in same workspace
# ============================================================================
def test_02_employee_cannot_retrieve_another_employees_approval_in_same_workspace(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    # Emp 1A attempts to access Emp 1B's approval
    headers = _auth_headers(env["employee1a"])
    target_id = env["approval1b"].id

    resp = client.get(f"/api/approvals/{target_id}", headers=headers)
    assert resp.status_code == 403
    assert "access denied" in resp.json()["detail"].lower()


# ============================================================================
# 3. Employee cannot retrieve approval from another workspace
# ============================================================================
def test_03_employee_cannot_retrieve_approval_from_another_workspace(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    # Emp 1A attempts to access Org 2's approval
    headers = _auth_headers(env["employee1a"])
    target_id = env["approval2"].id

    resp = client.get(f"/api/approvals/{target_id}", headers=headers)
    assert resp.status_code == 403
    assert "access denied" in resp.json()["detail"].lower()


# ============================================================================
# 4. Reviewer retrieves approvals in an authorized workspace
# ============================================================================
def test_04_reviewer_retrieves_approvals_in_authorized_workspace(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["reviewer1"])

    # Reviewer 1 can access Emp 1A's ticket
    resp1 = client.get(f"/api/approvals/{env['approval1a'].id}", headers=headers)
    assert resp1.status_code == 200
    assert resp1.json()["id"] == env["approval1a"].id

    # Reviewer 1 can access Emp 1B's ticket
    resp2 = client.get(f"/api/approvals/{env['approval1b'].id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == env["approval1b"].id

    # Reviewer 1 can list all workspace approvals
    resp_list = client.get(f"/api/workspaces/{env['ws1'].id}/approvals", headers=headers)
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) >= 2


# ============================================================================
# 5. Reviewer cannot retrieve approvals in an unauthorized workspace
# ============================================================================
def test_05_reviewer_cannot_retrieve_approvals_in_unauthorized_workspace(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["reviewer1"])

    # Attempt to access Org 2 approval ticket directly
    resp = client.get(f"/api/approvals/{env['approval2'].id}", headers=headers)
    assert resp.status_code == 403

    # Attempt to list Org 2 workspace queue
    resp_list = client.get(f"/api/workspaces/{env['ws2'].id}/approvals", headers=headers)
    assert resp_list.status_code == 403


# ============================================================================
# 6. Reviewer cannot decide an approval outside their workspace
# ============================================================================
def test_06_reviewer_cannot_decide_approval_outside_their_workspace(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["reviewer1"])
    target_id = env["approval2"].id

    # Attempt approve
    resp_appr = client.post(f"/api/approvals/{target_id}/approve", headers=headers)
    assert resp_appr.status_code == 403

    # Attempt request changes
    resp_rc = client.post(
        f"/api/approvals/{target_id}/request-changes",
        json={"comment": "Unauthorized change request"},
        headers=headers,
    )
    assert resp_rc.status_code == 403

    # Attempt reject
    resp_rej = client.post(
        f"/api/approvals/{target_id}/reject",
        json={"reason": "Unauthorized rejection"},
        headers=headers,
    )
    assert resp_rej.status_code == 403


# ============================================================================
# 7. Admin retains authorized workspace-wide access
# ============================================================================
def test_07_admin_retains_authorized_workspace_wide_access(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["admin1"])

    # Admin 1 can inspect both employees' tickets
    resp1 = client.get(f"/api/approvals/{env['approval1a'].id}", headers=headers)
    assert resp1.status_code == 200

    resp2 = client.get(f"/api/approvals/{env['approval1b'].id}", headers=headers)
    assert resp2.status_code == 200

    # Admin 1 can list all workspace approvals
    resp_list = client.get(f"/api/workspaces/{env['ws1'].id}/approvals", headers=headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 2

    # Admin 1 can legitimately approve ticket 1a
    resp_approve = client.post(f"/api/approvals/{env['approval1a'].id}/approve", headers=headers)
    assert resp_approve.status_code == 200
    assert resp_approve.json()["status"] == "approved"


# ============================================================================
# 8. Admin cannot access unrelated workspaces
# ============================================================================
def test_08_admin_cannot_access_unrelated_workspaces(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["admin1"])
    target_id = env["approval2"].id

    # Admin 1 cannot access Org 2 approval ticket
    resp = client.get(f"/api/approvals/{target_id}", headers=headers)
    assert resp.status_code == 403

    # Admin 1 cannot list Org 2 workspace queue
    resp_list = client.get(f"/api/workspaces/{env['ws2'].id}/approvals", headers=headers)
    assert resp_list.status_code == 403

    # Admin 1 cannot approve Org 2 ticket
    resp_approve = client.post(f"/api/approvals/{target_id}/approve", headers=headers)
    assert resp_approve.status_code == 403


# ============================================================================
# 9. Compatibility endpoints enforce the same access restrictions
# ============================================================================
def test_09_compatibility_endpoints_enforce_same_access_restrictions(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    rev1_headers = _auth_headers(env["reviewer1"])
    emp1_headers = _auth_headers(env["employee1a"])

    # 1. Reviewer 1 cannot access pending queue for Org 2 via compat route
    resp_q = client.get(f"/api/v1/approvals/pending?brand_id={env['ws2'].id}", headers=rev1_headers)
    assert resp_q.status_code == 403

    # 2. Reviewer 1 cannot approve Org 2 review via compat route
    resp_appr = client.post(f"/api/v1/approvals/{env['review2'].id}/approve", headers=rev1_headers)
    assert resp_appr.status_code == 403

    # 3. Reviewer 1 cannot request changes on Org 2 review via compat route
    resp_rc = client.post(
        f"/api/v1/approvals/{env['review2'].id}/request-changes",
        json={"comment": "Cross-workspace notes"},
        headers=rev1_headers,
    )
    assert resp_rc.status_code == 403

    # 4. Reviewer 1 cannot reject Org 2 review via compat route
    resp_rej = client.post(
        f"/api/v1/approvals/{env['review2'].id}/reject",
        json={"reason": "Cross-workspace reject"},
        headers=rev1_headers,
    )
    assert resp_rej.status_code == 403

    # 5. Employee cannot approve review via compat route
    resp_emp_appr = client.post(f"/api/v1/approvals/{env['review1a'].id}/approve", headers=emp1_headers)
    assert resp_emp_appr.status_code == 403


# ============================================================================
# 10. Revoked workspace membership prevents further access
# ============================================================================
def test_10_revoked_workspace_membership_prevents_further_access(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["revoked1"])

    # Revoked member cannot view ticket
    resp_get = client.get(f"/api/approvals/{env['approval1a'].id}", headers=headers)
    assert resp_get.status_code == 403

    # Revoked member cannot approve ticket
    resp_appr = client.post(f"/api/approvals/{env['approval1a'].id}/approve", headers=headers)
    assert resp_appr.status_code == 403

    # Revoked member cannot list workspace queue
    resp_list = client.get(f"/api/workspaces/{env['ws1'].id}/approvals", headers=headers)
    assert resp_list.status_code == 403

    # Revoked member cannot access compat pending queue
    resp_compat = client.get(f"/api/v1/approvals/pending?brand_id={env['ws1'].id}", headers=headers)
    assert resp_compat.status_code == 403


# ============================================================================
# 11. Superseded tickets remain readable as history but cannot be acted upon
# ============================================================================
def test_11_superseded_tickets_remain_readable_as_history_but_cannot_be_acted_upon(
    client: TestClient, auth_isolation_env, db: Session
):
    env = auth_isolation_env
    author = env["employee1a"]
    reviewer = env["reviewer1"]
    review = env["review1a"]
    t1 = env["approval1a"]

    # Advance review to v2 and request approval to supersede t1
    new_text = "Updated v2 copy for employee 1A that is fully compliant."
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content=new_text,
        user_id=author.id,
        change_description="v2 revisions",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    db.refresh(t1)
    assert t1.status == "superseded"
    assert t2.status == "pending"
    assert t2.version_number == 2

    # 1. Superseded ticket t1 is still readable as historical record by employee
    emp_headers = _auth_headers(author)
    resp_emp = client.get(f"/api/approvals/{t1.id}", headers=emp_headers)
    assert resp_emp.status_code == 200
    assert resp_emp.json()["status"] == "superseded"
    assert resp_emp.json()["version_number"] == 1

    # 2. Superseded ticket t1 is still readable by reviewer
    rev_headers = _auth_headers(reviewer)
    resp_rev = client.get(f"/api/approvals/{t1.id}", headers=rev_headers)
    assert resp_rev.status_code == 200
    assert resp_rev.json()["status"] == "superseded"

    # 3. Actionable pending queue excludes superseded ticket t1
    resp_queue = client.get(f"/api/workspaces/{env['ws1'].id}/approvals?status=pending", headers=rev_headers)
    assert resp_queue.status_code == 200
    queue_ids = [item["id"] for item in resp_queue.json()]
    assert t1.id not in queue_ids
    assert t2.id in queue_ids

    # 4. Compat pending queue excludes superseded ticket t1
    resp_compat_q = client.get(f"/api/v1/approvals/pending?brand_id={env['ws1'].id}", headers=rev_headers)
    assert resp_compat_q.status_code == 200
    compat_ids = [int(item["id"]) for item in resp_compat_q.json()]
    assert t1.id not in compat_ids
    assert t2.id in compat_ids

    # 5. Attempting to approve superseded ticket fails with HTTP 400
    resp_appr = client.post(f"/api/approvals/{t1.id}/approve", headers=rev_headers)
    assert resp_appr.status_code == 400
    assert "superseded" in resp_appr.json()["detail"].lower()

    # 6. Attempting to request changes on superseded ticket fails with HTTP 400
    resp_rc = client.post(
        f"/api/approvals/{t1.id}/request-changes",
        json={"comment": "Cannot request changes on superseded ticket"},
        headers=rev_headers,
    )
    assert resp_rc.status_code == 400
    assert "superseded" in resp_rc.json()["detail"].lower()

    # 7. Attempting to reject superseded ticket fails with HTTP 400
    resp_rej = client.post(
        f"/api/approvals/{t1.id}/reject",
        json={"reason": "Cannot reject superseded ticket"},
        headers=rev_headers,
    )
    assert resp_rej.status_code == 400
    assert "superseded" in resp_rej.json()["detail"].lower()


# ============================================================================
# 12. Employees cannot perform reviewer/admin decision actions
# ============================================================================
def test_12_employees_cannot_perform_reviewer_admin_decision_actions(client: TestClient, auth_isolation_env):
    env = auth_isolation_env
    headers = _auth_headers(env["employee1a"])
    own_ticket_id = env["approval1a"].id

    # 1. Employee cannot approve own ticket
    resp_appr = client.post(f"/api/approvals/{own_ticket_id}/approve", headers=headers)
    assert resp_appr.status_code == 403
    assert "Reviewer or Admin" in resp_appr.json()["detail"]

    # 2. Employee cannot request changes on own ticket
    resp_rc = client.post(
        f"/api/approvals/{own_ticket_id}/request-changes",
        json={"comment": "Self requesting changes"},
        headers=headers,
    )
    assert resp_rc.status_code == 403
    assert "Reviewer or Admin" in resp_rc.json()["detail"]

    # 3. Employee cannot reject own ticket
    resp_rej = client.post(
        f"/api/approvals/{own_ticket_id}/reject",
        json={"reason": "Self rejecting"},
        headers=headers,
    )
    assert resp_rej.status_code == 403
    assert "Reviewer or Admin" in resp_rej.json()["detail"]

    # 4. Employee cannot use legacy patch decision endpoint
    resp_patch = client.patch(
        f"/api/workspaces/{env['ws1'].id}/approvals/{own_ticket_id}?decision_status=approved",
        headers=headers,
    )
    assert resp_patch.status_code == 403


# ============================================================================
# 13. Changes_requested V1 ticket cannot approve a newer V2 ticket
# ============================================================================
def test_13_changes_requested_v1_ticket_cannot_approve_newer_v2_ticket(
    client: TestClient, auth_isolation_env, db: Session
):
    """
    Scenario 1: When a review has a stale changes_requested ticket for V1 and a newer
    pending ticket for V2, attempting to approve the stale ticket fails with HTTP 400
    and does NOT approve the V2 ticket.
    """
    env = auth_isolation_env
    author = env["employee1a"]
    reviewer = env["reviewer1"]
    review = env["review1a"]
    t1 = env["approval1a"]

    # 1. Reviewer requests changes on V1 ticket
    rev_headers = _auth_headers(reviewer)
    rc_res = client.post(
        f"/api/approvals/{t1.id}/request-changes",
        json={"comment": "Please address compliance issues in V1."},
        headers=rev_headers,
    )
    assert rc_res.status_code == 200
    db.refresh(t1)
    assert t1.status == "changes_requested"

    # 2. Author creates compliant V2 and requests approval
    v2_text = "Updated and verified compliant copy for V2."
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content=v2_text,
        user_id=author.id,
        change_description="V2 fixes",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    db.refresh(t2)
    assert t2.status == "pending"
    assert t2.version_number == 2

    # 3. Reviewer attempts to approve using stale V1 ticket ID
    stale_appr_res = client.post(f"/api/approvals/{t1.id}/approve", headers=rev_headers)
    assert stale_appr_res.status_code == 400
    assert "changes_requested" in stale_appr_res.json()["detail"].lower()

    # 4. Verify V2 ticket remains pending and unaffected
    db.refresh(t2)
    assert t2.status == "pending"
    assert t2.reviewer_id is None
    assert t2.version_number == 2


# ============================================================================
# 14. Stale V1 ticket cannot request changes on or reject the newer V2 ticket
# ============================================================================
def test_14_stale_v1_ticket_cannot_request_changes_or_reject_newer_v2_ticket(
    client: TestClient, auth_isolation_env, db: Session
):
    """
    Scenario 2: The same stale V1 ticket cannot request changes on or reject the newer V2 ticket.
    """
    env = auth_isolation_env
    author = env["employee1a"]
    reviewer = env["reviewer1"]
    review = env["review1a"]
    t1 = env["approval1a"]

    rev_headers = _auth_headers(reviewer)
    client.post(
        f"/api/approvals/{t1.id}/request-changes",
        json={"comment": "Initial revisions needed."},
        headers=rev_headers,
    )
    db.refresh(t1)
    assert t1.status == "changes_requested"

    # Author advances to V2
    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="V2 revision content for employee 1A.",
        user_id=author.id,
        change_description="V2 revision",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)
    db.refresh(t2)
    assert t2.status == "pending"
    assert t2.version_number == 2

    # Attempt request-changes on stale ticket
    rc_stale = client.post(
        f"/api/approvals/{t1.id}/request-changes",
        json={"comment": "Attempting changes on stale V1 ticket"},
        headers=rev_headers,
    )
    assert rc_stale.status_code == 400
    assert "changes_requested" in rc_stale.json()["detail"].lower()

    # Attempt reject on stale ticket
    rej_stale = client.post(
        f"/api/approvals/{t1.id}/reject",
        json={"reason": "Attempting reject on stale V1 ticket"},
        headers=rev_headers,
    )
    assert rej_stale.status_code == 400
    assert "changes_requested" in rej_stale.json()["detail"].lower()

    # Confirm V2 ticket remains pending and unaffected
    db.refresh(t2)
    assert t2.status == "pending"
    assert t2.reviewer_id is None
    assert t2.version_number == 2


# ============================================================================
# 15. Newer V2 ticket remains pending and unchanged after all stale-ticket attempts
# ============================================================================
def test_15_newer_v2_ticket_remains_pending_and_unchanged_after_all_stale_attempts(
    client: TestClient, auth_isolation_env, db: Session
):
    """
    Scenario 3: The newer V2 ticket remains pending and completely unchanged
    after sequential stale-ticket attempts (approve, request-changes, reject).
    """
    env = auth_isolation_env
    author = env["employee1a"]
    reviewer = env["reviewer1"]
    review = env["review1a"]
    t1 = env["approval1a"]

    rev_headers = _auth_headers(reviewer)
    client.post(
        f"/api/approvals/{t1.id}/request-changes",
        json={"comment": "Please revise copy for V1."},
        headers=rev_headers,
    )

    review_service.recheck_and_audit(
        db=db,
        review_id=review.id,
        new_content="Verified copy for version 2.",
        user_id=author.id,
        change_description="Version 2 update",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=review.id, user=author)

    t2_initial_version_id = t2.version_id
    t2_initial_content_hash = t2.content_hash
    t2_initial_version_number = t2.version_number

    # Execute all 3 operations on stale t1
    res1 = client.post(f"/api/approvals/{t1.id}/approve", headers=rev_headers)
    res2 = client.post(f"/api/approvals/{t1.id}/request-changes", json={"comment": "Stale RC"}, headers=rev_headers)
    res3 = client.post(f"/api/approvals/{t1.id}/reject", json={"reason": "Stale Rejection"}, headers=rev_headers)

    assert res1.status_code == 400
    assert res2.status_code == 400
    assert res3.status_code == 400

    # Ensure t2 remains strictly pending and unchanged in all attributes
    db.refresh(t2)
    assert t2.status == "pending"
    assert t2.reviewer_id is None
    assert t2.version_id == t2_initial_version_id
    assert t2.content_hash == t2_initial_content_hash
    assert t2.version_number == t2_initial_version_number

    # Ensure review is still pending
    db.refresh(review)
    assert review.status == "pending"


# ============================================================================
# 16. ID collision resolves strictly according to respective route contracts
# ============================================================================
def test_16_id_collision_resolves_strictly_according_to_route_contracts(
    client: TestClient, auth_isolation_env, db: Session
):
    """
    Scenario 4: When an Approval ticket ID and a ContentReview ID share the exact same integer value,
    - /api/approvals/{id}/approve strictly interprets {id} as Approval ID.
    - /api/v1/approvals/{id}/approve strictly interprets {id} as ContentReview ID.
    Neither endpoint guesses dynamically or confuses entity types.
    """
    env = auth_isolation_env
    author = env["employee1a"]
    reviewer = env["reviewer1"]
    rev_headers = _auth_headers(reviewer)

    # Pick a high unused integer to guarantee an unambiguous ID collision
    collision_id = 77777

    # Create ContentReview with id = collision_id
    clean_text = "Copy for collision review test."
    c_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    coll_review = ContentReview(
        id=collision_id,
        workspace_id=env["ws1"].id,
        submitted_by=author.id,
        title="Collision Review Test",
        content=clean_text,
        original_content=clean_text,
        content_type="article",
        status="pending",
        compliance_score=100,
        audit_status="verified",
        audited_content_hash=c_hash,
        current_version_number=1,
    )
    db.add(coll_review)
    db.flush()

    coll_version = ContentVersion(
        review_id=coll_review.id,
        version_number=1,
        content=clean_text,
        content_hash=c_hash,
        compliance_score=100,
        status="pending",
        audit_status="verified",
        findings_count=0,
        summary="Clean copy",
        change_description="Init",
        author_id=author.id,
    )
    db.add(coll_version)
    db.flush()

    # Active pending ticket for coll_review (ticket ID is autoincremented)
    coll_pending_ticket = Approval(
        review_id=coll_review.id,
        brand_rule_id=None,
        submitted_by=author.id,
        status="pending",
        version_id=coll_version.id,
        version_number=1,
        content_hash=c_hash,
        comment="Collision pending ticket",
    )
    db.add(coll_pending_ticket)
    db.flush()

    # Now create an Approval ticket with id = collision_id, belonging to review1b with status = "changes_requested"
    coll_ticket = Approval(
        id=collision_id,
        review_id=env["review1b"].id,
        brand_rule_id=None,
        submitted_by=author.id,
        status="changes_requested",
        version_id=env["review1b"].current_version_number,
        version_number=1,
        content_hash="abc123hash",
        comment="Stale ticket with collision ID",
    )
    db.add(coll_ticket)
    db.commit()

    assert coll_review.id == collision_id
    assert coll_ticket.id == collision_id

    # 1. Primary route contract: POST /api/approvals/{collision_id}/approve
    # Strictly evaluates Approval ticket with ID collision_id.
    # Since coll_ticket.status is 'changes_requested', it MUST return HTTP 400.
    res_api = client.post(f"/api/approvals/{collision_id}/approve", headers=rev_headers)
    assert res_api.status_code == 400
    assert "changes_requested" in res_api.json()["detail"].lower()

    # coll_pending_ticket must remain pending
    db.refresh(coll_pending_ticket)
    assert coll_pending_ticket.status == "pending"

    # 2. Legacy / compatibility contract: POST /api/v1/approvals/{collision_id}/approve
    # Strictly evaluates ContentReview with ID collision_id.
    # It resolves coll_review, finds its active pending ticket (coll_pending_ticket), and approves it!
    res_v1 = client.post(f"/api/v1/approvals/{collision_id}/approve", headers=rev_headers)
    assert res_v1.status_code == 200
    assert res_v1.json()["success"] is True
    assert res_v1.json()["status"] == "approved"

    # coll_pending_ticket is now approved
    db.refresh(coll_pending_ticket)
    assert coll_pending_ticket.status == "approved"

    # coll_ticket (Approval ticket 77777) was NEVER touched and remains changes_requested
    db.refresh(coll_ticket)
    assert coll_ticket.status == "changes_requested"


# ============================================================================
# 17. Legacy /api/v1 review-ID contract successfully acts on active pending ticket
# ============================================================================
def test_17_legacy_api_v1_review_id_contract_acts_on_active_pending_ticket(
    client: TestClient, auth_isolation_env, db: Session
):
    """
    Scenario 5: The legacy /api/v1 review-ID contract successfully acts on the correct
    active pending ticket for approve, request-changes, and reject.
    """
    env = auth_isolation_env
    author = env["employee1a"]
    reviewer = env["reviewer1"]
    rev_headers = _auth_headers(reviewer)

    # Test 1: Request changes via /api/v1/approvals/{review_id}/request-changes
    rev1 = env["review1a"]
    t1 = env["approval1a"]
    rc_res = client.post(
        f"/api/v1/approvals/{rev1.id}/request-changes",
        json={"revisionNotes": "Needs adjustments on paragraph 2."},
        headers=rev_headers,
    )
    assert rc_res.status_code == 200
    assert rc_res.json()["success"] is True
    assert rc_res.json()["status"] == "needs_changes"
    db.refresh(t1)
    assert t1.status == "changes_requested"

    # Test 2: Resubmit V2 and approve via /api/v1/approvals/{review_id}/approve
    review_service.recheck_and_audit(
        db=db,
        review_id=rev1.id,
        new_content="V2 revisions resolved completely.",
        user_id=author.id,
        change_description="V2 fixes",
    )
    t2 = approval_service.request_review_approval(db=db, review_id=rev1.id, user=author)
    assert t2.status == "pending"

    appr_res = client.post(f"/api/v1/approvals/{rev1.id}/approve", headers=rev_headers)
    assert appr_res.status_code == 200
    assert appr_res.json()["success"] is True
    assert appr_res.json()["status"] == "approved"
    db.refresh(t2)
    assert t2.status == "approved"

    # Test 3: Reject via /api/v1/approvals/{review_id}/reject on review1b
    rev2 = env["review1b"]
    t_b = env["approval1b"]
    rej_res = client.post(
        f"/api/v1/approvals/{rev2.id}/reject",
        json={"reason": "Cannot be approved due to business policy."},
        headers=rev_headers,
    )
    assert rej_res.status_code == 200
    assert rej_res.json()["success"] is True
    assert rej_res.json()["status"] == "rejected"
    db.refresh(t_b)
    assert t_b.status == "rejected"


# ============================================================================
# 18. Primary /api ticket-ID contract acts only on the exact ticket
# ============================================================================
def test_18_primary_api_ticket_id_contract_acts_only_on_exact_ticket(
    client: TestClient, auth_isolation_env, db: Session
):
    """
    Scenario 6: The primary /api ticket-ID contract acts only on the exact ticket specified in the path.
    """
    env = auth_isolation_env
    reviewer = env["reviewer1"]
    rev_headers = _auth_headers(reviewer)

    t = env["approval1a"]
    assert t.status == "pending"

    # Approve exact ticket via primary ticket route
    resp = client.post(f"/api/approvals/{t.id}/approve", headers=rev_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == t.id
    assert data["status"] == "approved"
    assert data["version_id"] == t.version_id
    assert data["content_hash"] == t.content_hash

    db.refresh(t)
    assert t.status == "approved"

    # Attempting to re-approve the exact ticket fails with 400
    repeat_res = client.post(f"/api/approvals/{t.id}/approve", headers=rev_headers)
    assert repeat_res.status_code == 400
    assert "already been approved" in repeat_res.json()["detail"].lower()


# ============================================================================
# 19. Cross-workspace and unauthorized-role restrictions remain enforced
# ============================================================================
def test_19_cross_workspace_and_unauthorized_role_restrictions_remain_enforced(
    client: TestClient, auth_isolation_env
):
    """
    Scenario 7: Cross-workspace and unauthorized-role restrictions remain strictly enforced
    across both /api and /api/v1 endpoints.
    """
    env = auth_isolation_env
    rev1_ticket = env["approval1a"]
    rev1_review = env["review1a"]

    # 1. User from Workspace 2 cannot approve WS1 review or ticket
    ws2_rev_headers = _auth_headers(env["reviewer2"])
    res_cross_v1 = client.post(f"/api/v1/approvals/{rev1_review.id}/approve", headers=ws2_rev_headers)
    assert res_cross_v1.status_code == 403

    res_cross_api = client.post(f"/api/approvals/{rev1_ticket.id}/approve", headers=ws2_rev_headers)
    assert res_cross_api.status_code == 403

    # 2. Employee in Workspace 1 cannot decide approvals
    emp_headers = _auth_headers(env["employee1a"])
    res_emp_v1 = client.post(f"/api/v1/approvals/{rev1_review.id}/approve", headers=emp_headers)
    assert res_emp_v1.status_code == 403

    res_emp_api = client.post(f"/api/approvals/{rev1_ticket.id}/approve", headers=emp_headers)
    assert res_emp_api.status_code == 403

    # 3. Revoked member cannot decide approvals
    revoked_headers = _auth_headers(env["revoked1"])
    res_rev_v1 = client.post(f"/api/v1/approvals/{rev1_review.id}/approve", headers=revoked_headers)
    assert res_rev_v1.status_code == 403

    res_rev_api = client.post(f"/api/approvals/{rev1_ticket.id}/approve", headers=revoked_headers)
    assert res_rev_api.status_code == 403
