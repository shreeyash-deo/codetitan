import pytest
from fastapi.testclient import TestClient
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.core.security import get_password_hash, create_access_token
from app.services.workspace_service import workspace_service


def setup_idempotency_environment(client, db, name="Idempotency Org"):
    slug = name.lower().replace(' ', '_')
    admin = User(
        name=f"Admin {name}",
        email=f"admin_{slug}@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role="User",
    )
    reviewer = User(
        name=f"Reviewer {name}",
        email=f"rev_{slug}@example.com",
        hashed_password=get_password_hash("RevPass123!"),
        role="User",
    )
    employee = User(
        name=f"Employee {name}",
        email=f"emp_{slug}@example.com",
        hashed_password=get_password_hash("EmpPass123!"),
        role="User",
    )
    db.add_all([admin, reviewer, employee])
    db.commit()
    db.refresh(admin)
    db.refresh(reviewer)
    db.refresh(employee)

    ws = Workspace(
        name=name,
        org_id=workspace_service.generate_org_id(db),
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    m_admin = WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="Admin", status="approved")
    m_rev = WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer", status="approved")
    m_emp = WorkspaceMember(workspace_id=ws.id, user_id=employee.id, role="Employee", status="approved")
    db.add_all([m_admin, m_rev, m_emp])
    db.commit()

    admin_token = create_access_token(subject=admin.id, extra_claims={"role": admin.role})
    rev_token = create_access_token(subject=reviewer.id, extra_claims={"role": reviewer.role})
    emp_token = create_access_token(subject=employee.id, extra_claims={"role": employee.role})

    # Seed approved rule
    rule = BrandRule(
        workspace_id=ws.id,
        title="Restricted Superlative Claims",
        description="Never use unsubstantiated superlative claims like 'world's fastest'.",
        category="Content restrictions",
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    return {
        "ws": ws,
        "admin": admin,
        "reviewer": reviewer,
        "employee": employee,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "rev_headers": {"Authorization": f"Bearer {rev_token}"},
        "emp_headers": {"Authorization": f"Bearer {emp_token}"},
    }


def test_first_approval_succeeds(client, db):
    """First approval by authorized reviewer succeeds, updates status, and issues certificate."""
    env = setup_idempotency_environment(client, db, "FirstApproval")
    ws_id = env["ws"].id

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Launch Copy",
            "content": "NovaPay provides secure cross-border payment processing.",
            "contentType": "Blog",
        },
        headers=env["emp_headers"],
    )
    assert scan_res.status_code == 200
    rev_id = int(scan_res.json()["id"])

    # Employee requests approval
    req_res = client.post(
        f"/api/v1/reviews/{rev_id}/request-approval",
        json={"comment": "Please review this launch copy."},
        headers=env["emp_headers"],
    )
    assert req_res.status_code == 201

    # Reviewer approves
    appr_res = client.post(
        f"/api/v1/approvals/{rev_id}/approve",
        json={"comment": "Looks good for production."},
        headers=env["rev_headers"],
    )
    assert appr_res.status_code == 200
    data = appr_res.json()
    assert data["status"] == "approved"
    assert data["success"] is True
    assert "certificateId" in data

    # Verify review in DB
    review = db.query(ContentReview).filter(ContentReview.id == rev_id).first()
    assert review.status == "approved"


def test_repeated_approval_rejected_no_duplicate_records(client, db):
    """Repeated approval attempts are rejected with 400 and create no duplicate records or events."""
    env = setup_idempotency_environment(client, db, "RepeatedApproval")
    ws_id = env["ws"].id

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Idempotent Asset",
            "content": "Institutional financial technology infrastructure.",
            "contentType": "Advertisement",
        },
        headers=env["emp_headers"],
    )
    rev_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{rev_id}/request-approval", json={"comment": "Sign-off needed"}, headers=env["emp_headers"])

    # 1. First approval
    first_res = client.post(
        f"/api/v1/approvals/{rev_id}/approve",
        json={"comment": "First sign-off"},
        headers=env["rev_headers"],
    )
    assert first_res.status_code == 200
    first_cert = first_res.json()["certificateId"]

    # Count activities and approvals after first approval
    act_count_1 = db.query(ReviewActivity).filter(
        ReviewActivity.review_id == rev_id,
        ReviewActivity.action == "Review approved",
    ).count()
    assert act_count_1 == 1

    appr_count_1 = db.query(Approval).filter(Approval.review_id == rev_id).count()

    # 2. Repeated approval call (double click / retry)
    repeat_res = client.post(
        f"/api/v1/approvals/{rev_id}/approve",
        json={"comment": "Second sign-off attempt"},
        headers=env["rev_headers"],
    )
    assert repeat_res.status_code == 400
    assert "already been approved" in repeat_res.json()["detail"].lower()

    # 3. Third approval attempt via canonical ticket endpoint if exists
    appr_obj = db.query(Approval).filter(Approval.review_id == rev_id).first()
    if appr_obj:
        repeat_ticket_res = client.post(
            f"/api/approvals/{appr_obj.id}/approve",
            headers=env["rev_headers"],
        )
        assert repeat_ticket_res.status_code == 400
        assert "already been approved" in repeat_ticket_res.json()["detail"].lower()

    # 4. Verify DB integrity: NO duplicate events or approval tickets
    act_count_2 = db.query(ReviewActivity).filter(
        ReviewActivity.review_id == rev_id,
        ReviewActivity.action == "Review approved",
    ).count()
    assert act_count_2 == 1, "Duplicate 'Review approved' activity was incorrectly created"

    appr_count_2 = db.query(Approval).filter(Approval.review_id == rev_id).count()
    assert appr_count_2 == appr_count_1, "Duplicate approval ticket was created"


def test_cannot_request_changes_on_already_approved_review(client, db):
    """An approved review cannot subsequently be modified by request-changes."""
    env = setup_idempotency_environment(client, db, "NoChangesAfterApprove")
    ws_id = env["ws"].id

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Completed Campaign",
            "content": "Fully verified and approved release.",
            "contentType": "Email",
        },
        headers=env["emp_headers"],
    )
    rev_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{rev_id}/request-approval", json={"comment": "Sign-off"}, headers=env["emp_headers"])

    # Approve
    client.post(f"/api/v1/approvals/{rev_id}/approve", headers=env["rev_headers"])

    # Attempt to request changes on approved review
    rc_res = client.post(
        f"/api/v1/approvals/{rev_id}/request-changes",
        json={"revisionNotes": "Actually rewrite this whole paragraph."},
        headers=env["rev_headers"],
    )
    assert rc_res.status_code == 400
    assert "already approved" in rc_res.json()["detail"].lower()

    # Verify review status remains approved
    review = db.query(ContentReview).filter(ContentReview.id == rev_id).first()
    assert review.status == "approved"


def test_request_changes_idempotency_and_resubmission_lifecycle(client, db):
    """
    1. Request changes transitions review to needs_revision and logs 1 activity.
    2. Repeated request-changes does not duplicate decision activities.
    3. Resubmission transitions review back to pending.
    4. Reviewer can then approve the resubmitted review.
    """
    env = setup_idempotency_environment(client, db, "LifecycleOrg")
    ws_id = env["ws"].id

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Social Campaign Draft",
            "content": "World's fastest checkout gateway.",
            "contentType": "Social",
        },
        headers=env["emp_headers"],
    )
    rev_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{rev_id}/request-approval", json={"comment": "First draft review"}, headers=env["emp_headers"])

    # Step 1: Reviewer requests changes
    rc1_res = client.post(
        f"/api/v1/approvals/{rev_id}/request-changes",
        json={"revisionNotes": "Remove 'world's fastest' claim."},
        headers=env["rev_headers"],
    )
    assert rc1_res.status_code == 200
    data = rc1_res.json()
    assert data["success"] is True

    review = db.query(ContentReview).filter(ContentReview.id == rev_id).first()
    assert review.status == "needs_revision"

    rc_act_count_1 = db.query(ReviewActivity).filter(
        ReviewActivity.review_id == rev_id,
        ReviewActivity.action == "Changes requested",
    ).count()
    assert rc_act_count_1 == 1

    # Step 2: Repeated request-changes (double click / retry)
    rc2_res = client.post(
        f"/api/v1/approvals/{rev_id}/request-changes",
        json={"revisionNotes": "Remove 'world's fastest' claim."},
        headers=env["rev_headers"],
    )
    assert rc2_res.status_code == 200

    rc_act_count_2 = db.query(ReviewActivity).filter(
        ReviewActivity.review_id == rev_id,
        ReviewActivity.action == "Changes requested",
    ).count()
    assert rc_act_count_2 == 1, "Repeated request-changes created duplicate activity event"

    # Step 3: Employee modifies content and resubmits
    resubmit_res = client.post(
        f"/api/v1/reviews/{rev_id}/request-approval",
        json={"comment": "I removed the superlative claim as requested."},
        headers=env["emp_headers"],
    )
    assert resubmit_res.status_code == 201

    db.refresh(review)
    assert review.status == "pending"

    # Step 4: Reviewer approves resubmitted review
    final_appr = client.post(
        f"/api/v1/approvals/{rev_id}/approve",
        json={"comment": "Changes look great, approved!"},
        headers=env["rev_headers"],
    )
    assert final_appr.status_code == 200
    assert final_appr.json()["status"] == "approved"

    db.refresh(review)
    assert review.status == "approved"


def test_concurrent_or_rapid_retry_approval_requests_exactly_one_succeeds(client, db):
    """
    When multiple rapid or retried approval requests are submitted for the same review
    (e.g. rapid double-clicking or duplicate concurrent client requests), exactly one
    succeeds with 200, all other attempts return 400 with a truthful error, and
    exactly one state transition and activity event occur.
    """
    env = setup_idempotency_environment(client, db, "ConcurrencyOrg")
    ws_id = env["ws"].id

    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "High Volume Concurrency Asset",
            "content": "Enterprise payment processing.",
            "contentType": "Blog",
        },
        headers=env["emp_headers"],
    )
    rev_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{rev_id}/request-approval", json={"comment": "Review ready"}, headers=env["emp_headers"])

    # Fire 3 rapid approval requests
    responses = [
        client.post(
            f"/api/v1/approvals/{rev_id}/approve",
            json={"comment": f"Concurrent approval attempt {i}"},
            headers=env["rev_headers"],
        )
        for i in range(3)
    ]

    status_codes = [r.status_code for r in responses]
    successes = [r for r in responses if r.status_code == 200]
    rejections = [r for r in responses if r.status_code == 400]

    assert len(successes) == 1, f"Expected exactly 1 successful approval, got {len(successes)}: {status_codes}"
    assert len(rejections) == 2, f"Expected 2 rejections, got {len(rejections)}: {status_codes}"

    for rej in rejections:
        assert "already been approved" in rej.json().get("detail", "").lower()

    # Confirm exactly 1 'Review approved' activity
    act_count = db.query(ReviewActivity).filter(
        ReviewActivity.review_id == rev_id,
        ReviewActivity.action == "Review approved",
    ).count()
    assert act_count == 1

    # Confirm review status is approved
    review = db.query(ContentReview).filter(ContentReview.id == rev_id).first()
    assert review.status == "approved"


def test_tenant_isolation_and_rbac_integrity(client, db):
    """Tenant isolation and role checks prevent unauthorized approval attempts."""
    org_a = setup_idempotency_environment(client, db, "AlphaOrg")
    org_b = setup_idempotency_environment(client, db, "BetaOrg")

    # Alpha creates review
    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(org_a["ws"].id),
            "title": "Alpha Review",
            "content": "Confidential Alpha corporate memo.",
            "contentType": "Email",
        },
        headers=org_a["emp_headers"],
    )
    rev_id = int(scan_res.json()["id"])
    client.post(f"/api/v1/reviews/{rev_id}/request-approval", json={"comment": "Sign-off"}, headers=org_a["emp_headers"])

    # 1. Employee in same org cannot approve
    emp_appr = client.post(f"/api/v1/approvals/{rev_id}/approve", headers=org_a["emp_headers"])
    assert emp_appr.status_code == 403

    # 2. Reviewer from DIFFERENT org cannot approve (tenant isolation)
    cross_appr = client.post(f"/api/v1/approvals/{rev_id}/approve", headers=org_b["rev_headers"])
    assert cross_appr.status_code == 403

    # 3. Legitimate reviewer in same org CAN approve
    auth_appr = client.post(f"/api/v1/approvals/{rev_id}/approve", headers=org_a["rev_headers"])
    assert auth_appr.status_code == 200
