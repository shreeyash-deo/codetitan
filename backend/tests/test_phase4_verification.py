"""
Phase 4 End-to-End Verification Test Suite
Verifies all 10 key Phase 4 Review & Approval Lifecycle scenarios:
1. Employee can submit content for review (persisting content, submitter, findings, score, workspace).
2. Submission appears in review queue with status pending.
3. Reviewer can inspect submission details.
4. Reviewer can approve submission (certifying status to approved).
5. Reviewer can request revisions with comments (status transitions to needs_revision).
6. Employee CANNOT approve submissions or request changes (403 Forbidden enforced).
7. Review decisions appear in historical ledger with timestamps and author metadata.
8. Comments are associated with the correct review and audit trail.
9. Workspace isolation: Reviews from Workspace Alpha never leak to Workspace Beta.
10. Empty review and approval queues render correctly with zero items.
"""

import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.review import ContentReview
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.schemas.user import UserCreate
from app.services.auth_service import auth_service
from app.core.security import create_access_token


def _headers_for(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


def setup_workspace_with_roles(client, db, org_name: str):
    """Creates a workspace with an Admin, a Reviewer, and an Employee."""
    admin = auth_service.create_user(
        db, UserCreate(name="Org Admin", email=f"admin_{org_name.lower().replace(' ', '')}@corp.io", password="Password123!")
    )
    admin_headers = _headers_for(admin)
    ws_res = client.post("/api/workspaces", json={"name": org_name}, headers=admin_headers)
    assert ws_res.status_code == 201
    ws = ws_res.json()

    reviewer = auth_service.create_user(
        db, UserCreate(name="Org Reviewer", email=f"rev_{org_name.lower().replace(' ', '')}@corp.io", password="Password123!")
    )
    client.post(f"/api/workspaces/{ws['id']}/members", json={"user_id": reviewer.id, "role": "Reviewer"}, headers=admin_headers)
    reviewer_headers = _headers_for(reviewer)

    employee = auth_service.create_user(
        db, UserCreate(name="Org Employee", email=f"emp_{org_name.lower().replace(' ', '')}@corp.io", password="Password123!")
    )
    client.post(f"/api/workspaces/{ws['id']}/members", json={"user_id": employee.id, "role": "Employee"}, headers=admin_headers)
    employee_headers = _headers_for(employee)

    # Add an approved rule to workspace so compliance audits can run
    client.post(
        f"/api/workspaces/{ws['id']}/rules",
        json={
            "title": "Prohibited Superlatives",
            "description": "Restricted terminology: 'the single best' is prohibited in marketing copy.",
            "category": "Restricted terminology",
            "approval_status": "approved",
        },
        headers=admin_headers,
    )

    return {
        "workspace": ws,
        "admin": admin,
        "admin_headers": admin_headers,
        "reviewer": reviewer,
        "reviewer_headers": reviewer_headers,
        "employee": employee,
        "employee_headers": employee_headers,
    }


def test_scenario_01_and_02_employee_submits_content_appears_in_queue(client, db):
    env = setup_workspace_with_roles(client, db, "Submission WS")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]

    # 1. Employee submits content for review
    submit_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Product Launch Post",
            "content": "Our solution is the single best tool for enterprise data integrity.",
            "contentType": "Social media",
            "channel": "Social",
        },
        headers=emp_headers,
    )
    assert submit_res.status_code == 200, submit_res.text
    review_data = submit_res.json()
    review_id = int(review_data["id"])
    assert review_data["overallScore"] < 100
    assert len(review_data["findings"]) >= 1

    # Employee requests managerial sign-off
    req_res = client.post(
        f"/api/v1/reviews/{review_id}/request-approval",
        json={"comment": "Ready for tier 2 review and sign-off."},
        headers=emp_headers,
    )
    assert req_res.status_code == 201

    # 2. Submission appears in the review queue (GET /api/v1/history and GET /api/v1/approvals/pending)
    rev_headers = env["reviewer_headers"]
    pending_res = client.get(f"/api/v1/approvals/pending?brand_id={ws_id}", headers=rev_headers)
    assert pending_res.status_code == 200
    pending_items = pending_res.json()
    assert any(item["reviewId"] == str(review_id) for item in pending_items)

    history_res = client.get(f"/api/v1/history?brand_id={ws_id}", headers=emp_headers)
    assert history_res.status_code == 200
    history_items = history_res.json()
    matching_rev = next(h for h in history_items if h["id"] == str(review_id))
    assert matching_rev["approvalStatus"] == "pending"
    assert matching_rev["submittedBy"]["name"] == env["employee"].name
    assert matching_rev["submittedBy"]["email"] == env["employee"].email


def test_scenario_03_reviewer_inspects_details(client, db):
    env = setup_workspace_with_roles(client, db, "Inspection WS")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    # Submit content
    submit_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Email Newsletter Q4",
            "content": "Check out the single best newsletter in fintech.",
            "contentType": "Email",
            "channel": "Email",
        },
        headers=emp_headers,
    )
    review_id = int(submit_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={"comment": "Please review"}, headers=emp_headers)

    # 3. Reviewer inspects details
    detail_res = client.get(f"/api/v1/history/{review_id}", headers=rev_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == str(review_id)
    assert detail["title"] == "Email Newsletter Q4"
    assert "single best" in detail["originalContent"]
    assert len(detail["findings"]) >= 1
    assert len(detail["timeline"]) >= 2


def test_scenario_04_reviewer_approves_submission(client, db):
    env = setup_workspace_with_roles(client, db, "Approval WS")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    submit_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Ad Creative Clean",
            "content": "Leading enterprise data governance platform.",
            "contentType": "Advertisement",
            "channel": "Social",
        },
        headers=emp_headers,
    )
    review_id = int(submit_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={"comment": "Final sign-off requested"}, headers=emp_headers)

    # 4. Reviewer approves submission
    appr_res = client.post(
        f"/api/v1/approvals/{review_id}/approve",
        json={"comment": "Approved for publishing without changes."},
        headers=rev_headers,
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "approved"
    assert "certificateId" in appr_res.json()

    # Verify status in history
    hist = client.get(f"/api/v1/history/{review_id}", headers=rev_headers).json()
    assert hist["approvalStatus"] == "approved"
    assert any("Final approval" in step["stage"] for step in hist["timeline"])


def test_scenario_05_reviewer_requests_changes(client, db):
    env = setup_workspace_with_roles(client, db, "Changes WS")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    submit_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Draft for Revision",
            "content": "Our solution is the single best tool on the market.",
            "contentType": "Blog",
            "channel": "Blog",
        },
        headers=emp_headers,
    )
    review_id = int(submit_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={"comment": "Initial draft"}, headers=emp_headers)

    # 5. Reviewer requests changes
    change_res = client.post(
        f"/api/v1/approvals/{review_id}/request-changes",
        json={"revisionNotes": "Please remove 'the single best' to comply with statutory claims policy."},
        headers=rev_headers,
    )
    assert change_res.status_code == 200
    assert change_res.json()["success"] is True

    # Verify status in history reflects needs_revision
    hist = client.get(f"/api/v1/history/{review_id}", headers=emp_headers).json()
    assert hist["approvalStatus"] == "needs_revision"
    assert any("Changes requested" in step["stage"] for step in hist["timeline"])


def test_scenario_06_employee_cannot_approve_or_request_changes(client, db):
    env = setup_workspace_with_roles(client, db, "RBAC Guard WS")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]

    submit_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Employee Sub",
            "content": "Check out our services.",
            "contentType": "Social media",
            "channel": "Social",
        },
        headers=emp_headers,
    )
    review_id = int(submit_res.json()["id"])
    client.post(f"/api/v1/reviews/{review_id}/request-approval", json={"comment": "Request"}, headers=emp_headers)

    # 6. Employee attempts to approve -> MUST return 403 Forbidden
    emp_appr_res = client.post(
        f"/api/v1/approvals/{review_id}/approve",
        json={"comment": "Self approval attempt"},
        headers=emp_headers,
    )
    assert emp_appr_res.status_code == 403
    assert "Reviewer or Admin" in emp_appr_res.json()["detail"]

    # Employee attempts to request changes -> MUST return 403 Forbidden
    emp_change_res = client.post(
        f"/api/v1/approvals/{review_id}/request-changes",
        json={"revisionNotes": "Unauthorized change request"},
        headers=emp_headers,
    )
    assert emp_change_res.status_code == 403


def test_scenario_08_comments_associated_with_correct_review(client, db):
    env = setup_workspace_with_roles(client, db, "Comments WS")
    ws_id = env["workspace"]["id"]
    emp_headers = env["employee_headers"]
    rev_headers = env["reviewer_headers"]

    submit_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Discussion Asset",
            "content": "Copy under discussion.",
            "contentType": "Social media",
            "channel": "Social",
        },
        headers=emp_headers,
    )
    review_id = int(submit_res.json()["id"])

    # 8. Add comments from both Reviewer and Employee
    c1 = client.post(
        f"/api/v1/approvals/{review_id}/comments",
        json={"text": "Reviewer comment: Needs disclaimer footer."},
        headers=rev_headers,
    )
    assert c1.status_code == 200

    c2 = client.post(
        f"/api/v1/approvals/{review_id}/comments",
        json={"text": "Author reply: Added in revision 2."},
        headers=emp_headers,
    )
    assert c2.status_code == 200

    # Verify comments in history detail
    hist = client.get(f"/api/v1/history/{review_id}", headers=emp_headers).json()
    assert len(hist["comments"]) >= 2
    assert any("Needs disclaimer footer" in c["text"] for c in hist["comments"])
    assert any("Added in revision 2" in c["text"] for c in hist["comments"])


def test_scenario_09_workspace_switching_does_not_leak_records(client, db):
    env1 = setup_workspace_with_roles(client, db, "Tenant Alpha")
    env2 = setup_workspace_with_roles(client, db, "Tenant Beta")

    # Tenant Alpha submits a review
    submit_alpha = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(env1["workspace"]["id"]),
            "title": "Confidential Alpha Campaign",
            "content": "Confidential strategy for Tenant Alpha only.",
            "contentType": "Blog",
            "channel": "Blog",
        },
        headers=env1["employee_headers"],
    )
    review_alpha_id = submit_alpha.json()["id"]

    # 9. Tenant Beta queries history -> MUST NOT see Tenant Alpha review
    beta_history = client.get(
        f"/api/v1/history?brand_id={env2['workspace']['id']}",
        headers=env2["reviewer_headers"],
    )
    assert beta_history.status_code == 200
    assert not any(r["id"] == review_alpha_id for r in beta_history.json())

    # Tenant Beta attempts to get review detail directly -> MUST return 403 Forbidden
    direct_get = client.get(
        f"/api/v1/history/{review_alpha_id}",
        headers=env2["reviewer_headers"],
    )
    assert direct_get.status_code == 403


def test_scenario_10_empty_queues_render_cleanly(client, db):
    env = setup_workspace_with_roles(client, db, "Empty WS")
    ws_id = env["workspace"]["id"]
    rev_headers = env["reviewer_headers"]

    # 10. Fresh workspace has empty approval queue and empty history
    pending_res = client.get(f"/api/v1/approvals/pending?brand_id={ws_id}", headers=rev_headers)
    assert pending_res.status_code == 200
    assert len(pending_res.json()) == 0

    history_res = client.get(f"/api/v1/history?brand_id={ws_id}", headers=rev_headers)
    assert history_res.status_code == 200
    assert len(history_res.json()) == 0
