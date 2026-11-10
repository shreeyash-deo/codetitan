import os
import sqlite3
import pytest
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.approval import Approval
from app.schemas.user import UserCreate
from app.schemas.workspace import WorkspaceCreate
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service
from app.core.security import create_access_token


def _headers_for(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


# 1. Registration cannot self-assign Admin or Reviewer
def test_registration_role_tampering_prevented(client):
    payload = {
        "name": "Attacker",
        "email": "attacker@corp.io",
        "password": "Password123!",
        "role": "Admin",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "User"
    assert data["email"] == "attacker@corp.io"


# 2. Workspace creator becomes Admin
def test_workspace_creator_becomes_admin(client, db):
    user = auth_service.create_user(
        db,
        UserCreate(name="Creator Alice", email="alice@test.io", password="Password123!"),
    )
    headers = _headers_for(user)

    res = client.post("/api/workspaces", json={"name": "Alice Workspace"}, headers=headers)
    assert res.status_code == 201
    ws_data = res.json()
    ws_id = ws_data["id"]

    members_res = client.get(f"/api/workspaces/{ws_id}/members", headers=headers)
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["user_id"] == user.id
    assert members[0]["role"] == "Admin"


# 3. Every workspace receives a unique public organisation ID
def test_workspace_unique_public_org_id_and_lookup(client, db):
    user = auth_service.create_user(
        db,
        UserCreate(name="Bob Org Lead", email="bob@test.io", password="Password123!"),
    )
    headers = _headers_for(user)

    ws1_res = client.post("/api/workspaces", json={"name": "Org Alpha"}, headers=headers)
    ws2_res = client.post("/api/workspaces", json={"name": "Org Beta"}, headers=headers)

    ws1 = ws1_res.json()
    ws2 = ws2_res.json()

    assert "org_id" in ws1
    assert "org_id" in ws2
    assert ws1["org_id"].startswith("ORG-")
    assert ws2["org_id"].startswith("ORG-")
    assert ws1["org_id"] != ws2["org_id"]

    # Public lookup test - must expose strictly name and org_id
    lookup_res = client.get(f"/api/workspaces/lookup?org_id={ws1['org_id']}")
    assert lookup_res.status_code == 200
    lookup_data = lookup_res.json()
    assert lookup_data["org_id"] == ws1["org_id"]
    assert lookup_data["name"] == "Org Alpha"
    assert "id" not in lookup_data
    assert "members" not in lookup_data

    # Non-existent lookup
    bad_lookup = client.get("/api/workspaces/lookup?org_id=ORG-NONEXISTENT")
    assert bad_lookup.status_code == 404


# 4. Global Admin without workspace membership is denied access
def test_global_admin_without_membership_is_denied(client, db):
    # Workspace owner
    owner = auth_service.create_user(
        db,
        UserCreate(name="Workspace Owner", email="owner_exclusive@corp.io", password="Password123!"),
    )
    owner_headers = _headers_for(owner)
    ws_res = client.post("/api/workspaces", json={"name": "Confidential Workspace"}, headers=owner_headers)
    ws_id = ws_res.json()["id"]

    # User with global role="Admin" in database, but NO membership in Confidential Workspace
    global_admin = auth_service.create_user(
        db,
        UserCreate(name="Global Admin User", email="global_admin@corp.io", password="Password123!"),
    )
    # Manually simulate a global Admin flag on user model
    global_admin.role = "Admin"
    db.commit()
    db.refresh(global_admin)

    admin_headers = _headers_for(global_admin)

    # All workspace-scoped routes must deny global admin access without membership
    endpoints_to_test = [
        ("GET", f"/api/workspaces/{ws_id}"),
        ("GET", f"/api/workspaces/{ws_id}/members"),
        ("GET", f"/api/workspaces/{ws_id}/guidelines"),
        ("GET", f"/api/workspaces/{ws_id}/rules"),
        ("GET", f"/api/workspaces/{ws_id}/reviews"),
        ("GET", f"/api/workspaces/{ws_id}/dashboard"),
    ]

    for method, path in endpoints_to_test:
        if method == "GET":
            r = client.get(path, headers=admin_headers)
        assert r.status_code == 403, f"Expected 403 for {path}, got {r.status_code}"
        assert "Access denied" in r.json()["detail"]


# 5. Admin, Reviewer, and Employee permission boundaries
def test_admin_reviewer_employee_permission_boundaries(client, db):
    admin = auth_service.create_user(db, UserCreate(name="Admin U", email="adm@co.io", password="Password123!"))
    reviewer = auth_service.create_user(db, UserCreate(name="Reviewer U", email="rev@co.io", password="Password123!"))
    employee = auth_service.create_user(db, UserCreate(name="Employee U", email="emp@co.io", password="Password123!"))

    admin_headers = _headers_for(admin)
    reviewer_headers = _headers_for(reviewer)
    employee_headers = _headers_for(employee)

    ws_res = client.post("/api/workspaces", json={"name": "RBAC Workspace"}, headers=admin_headers)
    ws_id = ws_res.json()["id"]

    # Admin adds Reviewer and Employee
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": reviewer.id, "role": "Reviewer"}, headers=admin_headers)
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": employee.id, "role": "Employee"}, headers=admin_headers)

    # 1. Guideline creation / upload:
    # Employee fails
    emp_upload = client.post(
        f"/api/workspaces/{ws_id}/guidelines",
        json={"filename": "brand.pdf", "file_path": "/tmp/brand.pdf", "extracted_text": "sample"},
        headers=employee_headers,
    )
    assert emp_upload.status_code == 403

    # Reviewer fails
    rev_upload = client.post(
        f"/api/workspaces/{ws_id}/guidelines",
        json={"filename": "brand.pdf", "file_path": "/tmp/brand.pdf", "extracted_text": "sample"},
        headers=reviewer_headers,
    )
    assert rev_upload.status_code == 403

    # Admin succeeds
    adm_upload = client.post(
        f"/api/workspaces/{ws_id}/guidelines",
        json={"filename": "brand.pdf", "file_path": "/tmp/brand.pdf", "extracted_text": "sample"},
        headers=admin_headers,
    )
    assert adm_upload.status_code == 201

    # 2. Rule creation:
    # Employee fails
    emp_rule = client.post(
        f"/api/workspaces/{ws_id}/rules",
        json={"title": "Primary Color", "description": "Always use Blue", "category": "Visual"},
        headers=employee_headers,
    )
    assert emp_rule.status_code == 403

    # Reviewer fails
    rev_rule = client.post(
        f"/api/workspaces/{ws_id}/rules",
        json={"title": "Primary Color", "description": "Always use Blue", "category": "Visual"},
        headers=reviewer_headers,
    )
    assert rev_rule.status_code == 403

    # Admin succeeds
    adm_rule = client.post(
        f"/api/workspaces/{ws_id}/rules",
        json={"title": "Primary Color", "description": "Always use Blue", "category": "Visual"},
        headers=admin_headers,
    )
    assert adm_rule.status_code == 201
    created_rule_id = adm_rule.json()["id"]

    # 3. Pending rule list:
    assert client.get(f"/api/workspaces/{ws_id}/rules/pending", headers=employee_headers).status_code == 403
    assert client.get(f"/api/workspaces/{ws_id}/rules/pending", headers=reviewer_headers).status_code == 403
    assert client.get(f"/api/workspaces/{ws_id}/rules/pending", headers=admin_headers).status_code == 200

    # 4. Employee can only view approved rules:
    emp_rules_view = client.get(f"/api/workspaces/{ws_id}/rules", headers=employee_headers).json()
    assert len(emp_rules_view) == 0  # because created rule is pending

    # Approve rule as Admin
    client.post(f"/api/rules/{created_rule_id}/approve", headers=admin_headers)

    # Now Employee can view it
    emp_rules_view2 = client.get(f"/api/workspaces/{ws_id}/rules", headers=employee_headers).json()
    assert len(emp_rules_view2) == 1
    assert emp_rules_view2[0]["id"] == created_rule_id


# 6. Reviewer cannot approve authoritative brand rules
def test_reviewer_cannot_approve_authoritative_brand_rules(client, db):
    admin = auth_service.create_user(db, UserCreate(name="Admin Guy", email="admg@test.io", password="Password123!"))
    reviewer = auth_service.create_user(db, UserCreate(name="Reviewer Gal", email="revg@test.io", password="Password123!"))

    admin_headers = _headers_for(admin)
    reviewer_headers = _headers_for(reviewer)

    ws_res = client.post("/api/workspaces", json={"name": "Rule Approval WS"}, headers=admin_headers)
    ws_id = ws_res.json()["id"]
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": reviewer.id, "role": "Reviewer"}, headers=admin_headers)

    rule_res = client.post(
        f"/api/workspaces/{ws_id}/rules",
        json={"title": "Rule Candidate", "description": "Font is Helvetica", "category": "Typography"},
        headers=admin_headers,
    )
    rule_id = rule_res.json()["id"]

    # Reviewer attempts direct approval -> 403
    rev_approve = client.post(f"/api/rules/{rule_id}/approve", headers=reviewer_headers)
    assert rev_approve.status_code == 403
    assert "Required workspace role: Admin" in rev_approve.json()["detail"]

    # Create approval ticket for this rule
    ticket_res = client.post(f"/api/rules/{rule_id}/request-approval", json={"comment": "Please approve font"}, headers=admin_headers)
    ticket_id = ticket_res.json()["id"]

    # Reviewer attempts ticket approval -> 403
    ticket_approve = client.post(f"/api/approvals/{ticket_id}/approve", headers=reviewer_headers)
    assert ticket_approve.status_code == 403
    assert "Only workspace Admin can decide this approval" in ticket_approve.json()["detail"]

    # Admin approves -> 200
    admin_approve = client.post(f"/api/approvals/{ticket_id}/approve", headers=admin_headers)
    assert admin_approve.status_code == 200
    assert admin_approve.json()["status"] == "approved"


# 7. Reviewer can approve content review submissions
def test_reviewer_can_approve_content_review_submissions(client, db):
    admin = auth_service.create_user(db, UserCreate(name="Admin Sub", email="admsub@test.io", password="Password123!"))
    reviewer = auth_service.create_user(db, UserCreate(name="Reviewer Sub", email="revsub@test.io", password="Password123!"))
    employee = auth_service.create_user(db, UserCreate(name="Employee Sub", email="empsub@test.io", password="Password123!"))

    admin_headers = _headers_for(admin)
    reviewer_headers = _headers_for(reviewer)
    employee_headers = _headers_for(employee)

    ws_res = client.post("/api/workspaces", json={"name": "Content WS"}, headers=admin_headers)
    ws_id = ws_res.json()["id"]
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": reviewer.id, "role": "Reviewer"}, headers=admin_headers)
    client.post(f"/api/workspaces/{ws_id}/members", json={"user_id": employee.id, "role": "Employee"}, headers=admin_headers)

    # Add and approve a rule so compliance scan succeeds
    r_res = client.post(f"/api/workspaces/{ws_id}/rules", json={"title": "Safe Copy", "description": "No banned words", "category": "Legal"}, headers=admin_headers)
    client.post(f"/api/rules/{r_res.json()['id']}/approve", headers=admin_headers)

    # Employee submits content review
    submission_res = client.post(
        f"/api/workspaces/{ws_id}/reviews",
        json={"title": "Q4 Press Release", "content": "NovaPay provides secure fast banking.", "content_type": "press_release"},
        headers=employee_headers,
    )
    assert submission_res.status_code == 201
    rev_id = submission_res.json()["id"]

    # Request approval ticket
    ticket_res = client.post(f"/api/reviews/{rev_id}/request-approval", json={"comment": "Review needed"}, headers=employee_headers)
    ticket_id = ticket_res.json()["id"]

    # Reviewer approves content submission ticket -> 200 OK!
    rev_decision = client.post(f"/api/approvals/{ticket_id}/approve", headers=reviewer_headers)
    assert rev_decision.status_code == 200
    assert rev_decision.json()["status"] == "approved"


# 8. Cross-organisation access is denied for all scoped resources
def test_cross_organisation_access_strictly_denied(client, db):
    user_a = auth_service.create_user(db, UserCreate(name="User A", email="usera@org1.io", password="Password123!"))
    user_b = auth_service.create_user(db, UserCreate(name="User B", email="userb@org2.io", password="Password123!"))

    headers_a = _headers_for(user_a)
    headers_b = _headers_for(user_b)

    ws_a_res = client.post("/api/workspaces", json={"name": "Org 1"}, headers=headers_a)
    ws_b_res = client.post("/api/workspaces", json={"name": "Org 2"}, headers=headers_b)

    ws_a_id = ws_a_res.json()["id"]
    ws_b_id = ws_b_res.json()["id"]

    # User A tries to access Org 2
    res = client.get(f"/api/workspaces/{ws_b_id}", headers=headers_a)
    assert res.status_code == 403

    res = client.get(f"/api/workspaces/{ws_b_id}/guidelines", headers=headers_a)
    assert res.status_code == 403

    res = client.get(f"/api/workspaces/{ws_b_id}/rules", headers=headers_a)
    assert res.status_code == 403

    res = client.get(f"/api/workspaces/{ws_b_id}/reviews", headers=headers_a)
    assert res.status_code == 403

    res = client.post(
        f"/api/workspaces/{ws_b_id}/members",
        json={"user_id": user_a.id, "role": "Admin"},
        headers=headers_a,
    )
    assert res.status_code == 403


# 9. Existing Editor memberships migrate to Employee
def test_legacy_editor_migrates_to_employee(db):
    user = auth_service.create_user(db, UserCreate(name="Legacy Ed", email="legacy@co.io", password="Password123!"))
    ws = Workspace(name="Legacy WS", org_id="ORG-LEGACY12")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # When add_member is called with "Editor", it normalizes to "Employee"
    member = workspace_service.add_member(db, ws.id, user.id, role="Editor")
    assert member.role == "Employee"


# 10. Existing records survive the migration
def test_existing_records_survive_migration():
    # Verify the real SQLite database file has preserved records
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brandshield.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        workspaces = cur.execute("SELECT id, org_id, name FROM workspaces").fetchall()
        assert len(workspaces) >= 2
        for w in workspaces:
            assert w[1] is not None
            assert w[1].startswith("ORG-")
            assert len(w[1]) == 12

        members = cur.execute("SELECT id, workspace_id, user_id, role FROM workspace_members").fetchall()
        assert len(members) >= 2
        for m in members:
            assert m[3] in ("Admin", "Reviewer", "Employee")

        conn.close()
