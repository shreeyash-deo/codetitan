"""
Employee Dashboard Scoping and Approval Access Verification Suite
Verifies:
1. Admin sees organization-wide dashboard metrics and telemetry.
2. Reviewer retains existing organization-wide reviewer dashboard access.
3. Employee sees only their own personal dashboard and submissions.
4. Employee sees empty states when they have no personal submissions.
5. Employee cannot see organization-wide approval counts or other employees' reviews.
6. Employee cannot view other employees' reviews via detail endpoints (403 Forbidden).
7. Employee cannot approve reviews (403 Forbidden).
8. Reviewer and Admin can view and approve reviews.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.approval import Approval
from app.models.finding import Finding
from app.models.activity import ReviewActivity
from app.core.security import get_password_hash, create_access_token
from app.services.workspace_service import workspace_service


def setup_scoping_workspace(db: Session):
    admin = User(
        name="Admin User",
        email="admin_scoping@brandshield.corp",
        hashed_password=get_password_hash("AdminPass123!"),
        role="User",
    )
    reviewer = User(
        name="Reviewer User",
        email="reviewer_scoping@brandshield.corp",
        hashed_password=get_password_hash("ReviewerPass123!"),
        role="User",
    )
    emp1 = User(
        name="Employee One",
        email="emp1_scoping@brandshield.corp",
        hashed_password=get_password_hash("EmpPass123!"),
        role="User",
    )
    emp2 = User(
        name="Employee Two",
        email="emp2_scoping@brandshield.corp",
        hashed_password=get_password_hash("EmpPass123!"),
        role="User",
    )
    db.add_all([admin, reviewer, emp1, emp2])
    db.commit()
    for u in [admin, reviewer, emp1, emp2]:
        db.refresh(u)

    ws = Workspace(
        name="Scoping Corp",
        org_id=workspace_service.generate_org_id(db),
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # Add memberships
    m_admin = WorkspaceMember(workspace_id=ws.id, user_id=admin.id, role="Admin")
    m_reviewer = WorkspaceMember(workspace_id=ws.id, user_id=reviewer.id, role="Reviewer")
    m_emp1 = WorkspaceMember(workspace_id=ws.id, user_id=emp1.id, role="Employee")
    m_emp2 = WorkspaceMember(workspace_id=ws.id, user_id=emp2.id, role="Employee")
    db.add_all([m_admin, m_reviewer, m_emp1, m_emp2])
    db.commit()

    tokens = {
        "admin": create_access_token(subject=admin.id, extra_claims={"role": "User"}),
        "reviewer": create_access_token(subject=reviewer.id, extra_claims={"role": "User"}),
        "emp1": create_access_token(subject=emp1.id, extra_claims={"role": "User"}),
        "emp2": create_access_token(subject=emp2.id, extra_claims={"role": "User"}),
    }

    headers = {k: {"Authorization": f"Bearer {v}"} for k, v in tokens.items()}

    return {
        "ws": ws,
        "admin": admin,
        "reviewer": reviewer,
        "emp1": emp1,
        "emp2": emp2,
        "headers": headers,
    }


def test_employee_with_no_submissions_sees_clean_empty_state(client: TestClient, db: Session):
    """An employee with no submissions sees empty state (0 reviews, 0 pending, has_reviews: false)."""
    env = setup_scoping_workspace(db)
    ws_id = env["ws"].id
    headers_emp2 = env["headers"]["emp2"]

    # 1. Direct workspace dashboard endpoint
    res = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=headers_emp2)
    assert res.status_code == 200
    data = res.json()
    assert data["total_reviews"] == 0
    assert data["has_reviews"] is False
    assert data["pending_approvals"] == 0
    assert data["critical_findings"] == 0
    assert len(data["recent_reviews"]) == 0
    assert len(data["recent_activity"]) == 0
    assert len(data["violations_by_category"]) == 0

    # 2. Compat telemetry endpoint
    tel_res = client.get(f"/api/v1/brands/{ws_id}/telemetry", headers=headers_emp2)
    assert tel_res.status_code == 200
    tel_data = tel_res.json()
    assert tel_data["contentReviewedCount"] == 0
    assert tel_data["hasReviews"] is False
    assert tel_data["pendingApprovalsCount"] == 0
    assert tel_data["criticalIssuesCount"] == 0
    assert len(tel_data["violationsByCategory"]) == 0
    assert len(tel_data["recentActivity"]) == 0

    # 3. History endpoint
    hist_res = client.get(f"/api/v1/history?brand_id={ws_id}", headers=headers_emp2)
    assert hist_res.status_code == 200
    assert hist_res.json() == []


def test_employee_dashboard_scoping_isolation(client: TestClient, db: Session):
    """
    When Employee 1 submits a review and requests approval:
    - Employee 1 sees their 1 review and 1 pending approval.
    - Employee 2 (who submitted nothing) still sees 0 reviews and 0 pending approvals.
    - Admin sees 1 review and 1 pending approval across the organization.
    - Reviewer sees 1 review and 1 pending approval across the organization.
    """
    env = setup_scoping_workspace(db)
    ws_id = env["ws"].id
    headers_admin = env["headers"]["admin"]
    headers_reviewer = env["headers"]["reviewer"]
    headers_emp1 = env["headers"]["emp1"]
    headers_emp2 = env["headers"]["emp2"]

    # Create approved rule so scan works
    rule = BrandRule(
        workspace_id=ws_id,
        title="Prohibit Absolute Guarantees",
        description="Never guarantee 100% results.",
        category="Content Restrictions",
        confidence=0.95,
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    # Employee 1 submits review
    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Employee 1 Ad Campaign",
            "content": "This offer has a 100% guarantee.",
            "contentType": "Advertisement",
            "channel": "Social",
        },
        headers=headers_emp1,
    )
    assert scan_res.status_code == 200
    rev1_id = scan_res.json()["id"]

    # Employee 1 requests approval
    req_res = client.post(
        f"/api/v1/reviews/{rev1_id}/request-approval",
        json={"comment": "Please review my campaign"},
        headers=headers_emp1,
    )
    assert req_res.status_code == 201

    # Check Employee 1 dashboard
    emp1_dash = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=headers_emp1).json()
    assert emp1_dash["total_reviews"] == 1
    assert emp1_dash["has_reviews"] is True
    assert emp1_dash["pending_approvals"] == 1
    assert len(emp1_dash["recent_reviews"]) == 1
    assert emp1_dash["recent_reviews"][0]["title"] == "Employee 1 Ad Campaign"

    # Employee 1 lists workspace approvals -> sees only their 1 approval
    emp1_appr = client.get(f"/api/workspaces/{ws_id}/approvals", headers=headers_emp1).json()
    assert len(emp1_appr) == 1

    # Check Employee 2 dashboard (must remain empty!)
    emp2_dash = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=headers_emp2).json()
    assert emp2_dash["total_reviews"] == 0
    assert emp2_dash["has_reviews"] is False
    assert emp2_dash["pending_approvals"] == 0
    assert len(emp2_dash["recent_reviews"]) == 0
    assert len(emp2_dash["recent_activity"]) == 0

    # Employee 2 lists workspace approvals -> must be empty (0 approvals)
    emp2_appr = client.get(f"/api/workspaces/{ws_id}/approvals", headers=headers_emp2).json()
    assert len(emp2_appr) == 0

    # Check Employee 2 telemetry (must remain 0!)
    emp2_tel = client.get(f"/api/v1/brands/{ws_id}/telemetry", headers=headers_emp2).json()
    assert emp2_tel["contentReviewedCount"] == 0
    assert emp2_tel["hasReviews"] is False
    assert emp2_tel["pendingApprovalsCount"] == 0
    assert len(emp2_tel["recentActivity"]) == 0

    # Check Employee 2 history (must be empty!)
    emp2_hist = client.get(f"/api/v1/history?brand_id={ws_id}", headers=headers_emp2).json()
    assert len(emp2_hist) == 0

    # Check Admin dashboard (must see organization-wide review!)
    admin_dash = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=headers_admin).json()
    assert admin_dash["total_reviews"] == 1
    assert admin_dash["has_reviews"] is True
    assert admin_dash["pending_approvals"] == 1
    assert len(admin_dash["recent_reviews"]) == 1

    # Check Reviewer dashboard (must see organization-wide review!)
    rev_dash = client.get(f"/api/v1/workspaces/{ws_id}/dashboard", headers=headers_reviewer).json()
    assert rev_dash["total_reviews"] == 1
    assert rev_dash["has_reviews"] is True
    assert rev_dash["pending_approvals"] == 1
    assert len(rev_dash["recent_reviews"]) == 1


def test_employee_cross_review_access_forbidden(client: TestClient, db: Session):
    """An employee attempting to view or access another employee's review receives 403 Forbidden."""
    env = setup_scoping_workspace(db)
    ws_id = env["ws"].id
    headers_emp1 = env["headers"]["emp1"]
    headers_emp2 = env["headers"]["emp2"]
    headers_reviewer = env["headers"]["reviewer"]

    # Rule
    rule = BrandRule(
        workspace_id=ws_id,
        title="Clarity Standard",
        description="Write clearly.",
        category="Brand Voice",
        confidence=0.9,
        approval_status="approved",
    )
    db.add(rule)
    db.commit()

    # Employee 1 creates review
    scan_res = client.post(
        "/api/v1/reviews/scan",
        json={
            "brandId": str(ws_id),
            "title": "Confidential Employee 1 Copy",
            "content": "Clear and professional message.",
            "contentType": "Email",
            "channel": "Email",
        },
        headers=headers_emp1,
    )
    assert scan_res.status_code == 200
    rev1_id = scan_res.json()["id"]

    # Employee 1 can read their own review
    emp1_view = client.get(f"/api/v1/reviews/{rev1_id}", headers=headers_emp1)
    assert emp1_view.status_code == 200

    emp1_hist = client.get(f"/api/v1/history/{rev1_id}", headers=headers_emp1)
    assert emp1_hist.status_code == 200

    # Employee 2 attempts to read Employee 1's review -> 403 Forbidden
    emp2_view = client.get(f"/api/v1/reviews/{rev1_id}", headers=headers_emp2)
    assert emp2_view.status_code == 403
    assert "Employees may only view their own submitted reviews" in emp2_view.json()["detail"]

    emp2_hist = client.get(f"/api/v1/history/{rev1_id}", headers=headers_emp2)
    assert emp2_hist.status_code == 403
    assert "Employees may only view their own submitted reviews" in emp2_hist.json()["detail"]

    # Reviewer CAN read Employee 1's review
    reviewer_view = client.get(f"/api/v1/reviews/{rev1_id}", headers=headers_reviewer)
    assert reviewer_view.status_code == 200


def test_employee_approval_blocked_while_reviewer_and_admin_allowed(client: TestClient, db: Session):
    """
    Employee cannot approve content (403 Forbidden).
    Reviewer and Admin can approve content (200 OK).
    """
    env = setup_scoping_workspace(db)
    ws_id = env["ws"].id
    headers_emp1 = env["headers"]["emp1"]
    headers_reviewer = env["headers"]["reviewer"]
    headers_admin = env["headers"]["admin"]

    # Review submitted by Employee 1
    review = ContentReview(
        workspace_id=ws_id,
        title="Feature Launch Copy",
        content="New feature launch text.",
        original_content="New feature launch text.",
        content_type="social_media",
        status="in_review",
        compliance_score=92,
        submitted_by=env["emp1"].id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    req_res = client.post(
        f"/api/v1/reviews/{review.id}/request-approval",
        json={"comment": "Ready for approval"},
        headers=headers_emp1,
    )
    assert req_res.status_code in (200, 201)
    approval_id = req_res.json()["id"]

    # Employee attempt to approve -> 403 Forbidden
    emp_appr = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"comment": "I approve my own work"},
        headers=headers_emp1,
    )
    assert emp_appr.status_code == 403
    assert "Required workspace role: Reviewer or Admin" in emp_appr.json()["detail"]

    # Reviewer approves -> 200 OK
    rev_appr = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        json={"comment": "Approved by reviewer"},
        headers=headers_reviewer,
    )
    assert rev_appr.status_code == 200
    assert rev_appr.json()["status"] == "approved"
