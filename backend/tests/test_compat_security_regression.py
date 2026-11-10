import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.review import ContentReview
from app.models.approval import Approval
from app.models.activity import ReviewActivity
from app.schemas.user import UserCreate
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service
from app.core.security import create_access_token


def _headers_for(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def org_setup(db):
    """Sets up two distinct workspaces with users across different roles."""
    # Org A Users
    user_a_admin = auth_service.create_user(
        db, UserCreate(name="Alice Admin", email="alice.admin@orga.io", password="Password123!")
    )
    user_a_reviewer = auth_service.create_user(
        db, UserCreate(name="Aaron Reviewer", email="aaron.reviewer@orga.io", password="Password123!")
    )
    user_a_employee = auth_service.create_user(
        db, UserCreate(name="Amy Employee", email="amy.employee@orga.io", password="Password123!")
    )

    # Org B Users
    user_b_admin = auth_service.create_user(
        db, UserCreate(name="Bob Admin", email="bob.admin@orgb.io", password="Password123!")
    )
    user_b_employee = auth_service.create_user(
        db, UserCreate(name="Brian Employee", email="brian.employee@orgb.io", password="Password123!")
    )

    # Workspaces
    ws_a = Workspace(name="Organisation A", org_id="ORG-AAAA1111")
    ws_b = Workspace(name="Organisation B", org_id="ORG-BBBB2222")
    db.add_all([ws_a, ws_b])
    db.commit()
    db.refresh(ws_a)
    db.refresh(ws_b)

    # Memberships
    members = [
        WorkspaceMember(workspace_id=ws_a.id, user_id=user_a_admin.id, role="Admin"),
        WorkspaceMember(workspace_id=ws_a.id, user_id=user_a_reviewer.id, role="Reviewer"),
        WorkspaceMember(workspace_id=ws_a.id, user_id=user_a_employee.id, role="Employee"),
        WorkspaceMember(workspace_id=ws_b.id, user_id=user_b_admin.id, role="Admin"),
        WorkspaceMember(workspace_id=ws_b.id, user_id=user_b_employee.id, role="Employee"),
    ]
    db.add_all(members)
    db.commit()

    # Content Review in Org A
    review_a = ContentReview(
        workspace_id=ws_a.id,
        title="Org A Marketing Campaign",
        content="Welcome to Organisation A services.",
        original_content="Welcome to Organisation A services.",
        content_type="social_media",
        status="in_review",
        compliance_score=85,
        submitted_by=user_a_employee.id,
    )
    db.add(review_a)
    db.commit()
    db.refresh(review_a)

    return {
        "ws_a": ws_a,
        "ws_b": ws_b,
        "review_a": review_a,
        "user_a_admin": user_a_admin,
        "user_a_reviewer": user_a_reviewer,
        "user_a_employee": user_a_employee,
        "user_b_admin": user_b_admin,
        "user_b_employee": user_b_employee,
    }


# ============================================================================
# 1. SEC-01: Review History Isolation (GET /api/history/{id})
# ============================================================================

def test_sec01_review_history_cross_tenant_access_denied(client, org_setup):
    review_id = org_setup["review_a"].id

    # Authorized member of Org A can access
    headers_a = _headers_for(org_setup["user_a_employee"])
    res_a = client.get(f"/api/history/{review_id}", headers=headers_a)
    assert res_a.status_code == 200
    data = res_a.json()
    assert data["id"] == str(review_id)
    assert data["title"] == "Org A Marketing Campaign"

    # User belonging to Org B is rejected
    headers_b = _headers_for(org_setup["user_b_admin"])
    res_b = client.get(f"/api/history/{review_id}", headers=headers_b)
    assert res_b.status_code == 403
    assert "not a member of the workspace" in res_b.json()["detail"]

    # Non-existent review ID returns 404
    res_404 = client.get("/api/history/99999", headers=headers_a)
    assert res_404.status_code == 404


# ============================================================================
# 2. SEC-02: Review Approval Role Restrictions (POST /api/approvals/{id}/approve)
# ============================================================================

def test_sec02_approve_content_role_restrictions(client, org_setup, db):
    review = org_setup["review_a"]

    # 1. Cross-organisation user cannot approve
    headers_b = _headers_for(org_setup["user_b_admin"])
    res_b = client.post(f"/api/approvals/{review.id}/approve", headers=headers_b)
    assert res_b.status_code == 403

    # 2. Employee in Org A cannot approve
    headers_emp = _headers_for(org_setup["user_a_employee"])
    res_emp = client.post(f"/api/approvals/{review.id}/approve", headers=headers_emp)
    assert res_emp.status_code == 403
    assert "Reviewer or Admin" in res_emp.json()["detail"]

    # 3. Reviewer in Org A can approve
    headers_rev = _headers_for(org_setup["user_a_reviewer"])
    res_rev = client.post(
        f"/api/approvals/{review.id}/approve",
        json={"comment": "Approved by verified reviewer"},
        headers=headers_rev,
    )
    assert res_rev.status_code == 200
    assert res_rev.json()["success"] is True
    assert res_rev.json()["status"] == "approved"

    # Verify review status is now approved
    db.refresh(review)
    assert review.status == "approved"


# ============================================================================
# 3. SEC-03: Request Changes Role Restrictions (POST /api/approvals/{id}/request-changes)
# ============================================================================

def test_sec03_request_changes_role_restrictions(client, org_setup, db):
    review = org_setup["review_a"]

    # 1. Cross-tenant user cannot request changes
    headers_b = _headers_for(org_setup["user_b_admin"])
    res_b = client.post(
        f"/api/approvals/{review.id}/request-changes",
        json={"revisionNotes": "Malicious change request"},
        headers=headers_b,
    )
    assert res_b.status_code == 403

    # 2. Employee cannot request changes
    headers_emp = _headers_for(org_setup["user_a_employee"])
    res_emp = client.post(
        f"/api/approvals/{review.id}/request-changes",
        json={"revisionNotes": "Employee requesting changes"},
        headers=headers_emp,
    )
    assert res_emp.status_code == 403
    assert "Reviewer or Admin" in res_emp.json()["detail"]

    # 3. Admin can request changes
    headers_adm = _headers_for(org_setup["user_a_admin"])
    res_adm = client.post(
        f"/api/approvals/{review.id}/request-changes",
        json={"revisionNotes": "Please clarify terms and conditions"},
        headers=headers_adm,
    )
    assert res_adm.status_code == 200
    assert res_adm.json()["success"] is True

    # Verify review status was set to needs_revision
    db.refresh(review)
    assert review.status == "needs_revision"


# ============================================================================
# 4. SEC-04: Review Comments Scoping (POST /api/approvals/{id}/comments)
# ============================================================================

def test_sec04_review_comments_tenant_scoping(client, org_setup, db):
    review = org_setup["review_a"]

    # 1. Non-member cannot add comment
    headers_b = _headers_for(org_setup["user_b_employee"])
    res_b = client.post(
        f"/api/approvals/{review.id}/comments",
        json={"text": "Unauthorised comment from Org B"},
        headers=headers_b,
    )
    assert res_b.status_code == 403
    assert "not a member of the workspace" in res_b.json()["detail"]

    # 2. Non-existent review returns 404
    headers_a = _headers_for(org_setup["user_a_employee"])
    res_404 = client.post(
        "/api/approvals/88888/comments",
        json={"text": "Comment on ghost review"},
        headers=headers_a,
    )
    assert res_404.status_code == 404

    # 3. Legitimate workspace member can comment and workspace_id is preserved
    res_ok = client.post(
        f"/api/approvals/{review.id}/comments",
        json={"text": "Updated paragraph 3 as discussed."},
        headers=headers_a,
    )
    assert res_ok.status_code == 200
    comment_data = res_ok.json()
    assert comment_data["text"] == "Updated paragraph 3 as discussed."

    # Verify the activity record in database has the correct workspace_id
    activity = db.query(ReviewActivity).filter(ReviewActivity.review_id == review.id).first()
    assert activity is not None
    assert activity.workspace_id == org_setup["ws_a"].id
    assert activity.user_id == org_setup["user_a_employee"].id


# ============================================================================
# 5. SEC-05: Strict Workspace Lookup (No Silent Fallback)
# ============================================================================

def test_sec05_unauthorized_or_invalid_brand_id_never_falls_back(client, org_setup):
    ws_b = org_setup["ws_b"]
    headers_a = _headers_for(org_setup["user_a_admin"])

    # 1. Passing another organisation's numeric ID must return 403 (not fall back to Org A)
    res_unauth = client.get(f"/api/history?brand_id={ws_b.id}", headers=headers_a)
    assert res_unauth.status_code == 403
    assert "Access denied" in res_unauth.json()["detail"]

    # 2. Passing another organisation's public org_id must return 403
    res_unauth_code = client.get(f"/api/history?brand_id={ws_b.org_id}", headers=headers_a)
    assert res_unauth_code.status_code == 403
    assert "Access denied" in res_unauth_code.json()["detail"]

    # 3. Passing a non-existent workspace ID must return 404
    res_nonexistent = client.get("/api/history?brand_id=99999", headers=headers_a)
    assert res_nonexistent.status_code == 404
    assert "Workspace not found" in res_nonexistent.json()["detail"]

    # 4. Same strict rejection on telemetry endpoint
    res_telem_unauth = client.get(f"/api/brands/{ws_b.id}/telemetry", headers=headers_a)
    assert res_telem_unauth.status_code == 403

    # 5. Same strict rejection on pending approvals endpoint
    res_appr_unauth = client.get(f"/api/approvals/pending?brand_id={ws_b.id}", headers=headers_a)
    assert res_appr_unauth.status_code == 403

    # 6. Valid authorised workspace ID succeeds as expected
    res_auth = client.get(f"/api/history?brand_id={org_setup['ws_a'].id}", headers=headers_a)
    assert res_auth.status_code == 200
