"""
Strict RBAC Matrix Security Regression Suite
Verifies all 16 core permission boundaries between Admin, Reviewer, and Employee roles,
as well as cross-tenant isolation in BrandShield.
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.rule import BrandRule
from app.models.review import ContentReview
from app.models.approval import Approval
from app.schemas.user import UserCreate
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service
from app.core.security import create_access_token


def make_auth_header(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


def make_user(db: Session, email: str, name: str) -> User:
    return auth_service.create_user(
        db,
        UserCreate(name=name, email=email, password="Password123!"),
    )


@pytest.fixture
def rbac_fixture(db: Session):
    """Sets up primary workspace (Org Alpha) with Admin, Reviewer, and Employee,
    plus an isolated secondary workspace (Org Beta) with its own Admin and Employee."""
    # Org Alpha Users
    admin_a = make_user(db, "alpha_admin@example.com", "Alpha Admin")
    reviewer_a = make_user(db, "alpha_reviewer@example.com", "Alpha Reviewer")
    employee_a = make_user(db, "alpha_employee@example.com", "Alpha Employee")

    ws_a = workspace_service.create_workspace(db, name="Alpha Corp", creator_id=admin_a.id)
    # Add Reviewer and Employee to Alpha Corp as approved members
    workspace_service.add_member(db, ws_a.id, reviewer_a.id, role="Reviewer")
    workspace_service.add_member(db, ws_a.id, employee_a.id, role="Employee")

    # Org Beta Users & Workspace
    admin_b = make_user(db, "beta_admin@example.com", "Beta Admin")
    employee_b = make_user(db, "beta_employee@example.com", "Beta Employee")
    ws_b = workspace_service.create_workspace(db, name="Beta Corp", creator_id=admin_b.id)
    workspace_service.add_member(db, ws_b.id, employee_b.id, role="Employee")

    return {
        "ws_a": ws_a,
        "ws_b": ws_b,
        "admin_a": admin_a,
        "reviewer_a": reviewer_a,
        "employee_a": employee_a,
        "admin_b": admin_b,
        "employee_b": employee_b,
        "headers_admin_a": make_auth_header(admin_a),
        "headers_reviewer_a": make_auth_header(reviewer_a),
        "headers_employee_a": make_auth_header(employee_a),
        "headers_admin_b": make_auth_header(admin_b),
        "headers_employee_b": make_auth_header(employee_b),
    }


class TestStrictRBACMatrix:
    """16 required RBAC security tests verifying role enforcement and cross-tenant isolation."""

    # 1. Admin can upload guidelines
    def test_01_admin_can_upload_guidelines(self, client: TestClient, rbac_fixture):
        ws_id = rbac_fixture["ws_a"].id
        headers = rbac_fixture["headers_admin_a"]

        file_payload = {
            "file": ("brand_manual.txt", io.BytesIO(b"Brand Voice: Transparent and direct."), "text/plain")
        }
        res = client.post(f"/api/v1/workspaces/{ws_id}/guidelines/upload", files=file_payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["filename"] == "brand_manual.txt"
        assert data["workspace_id"] == ws_id

    # 2. Employee cannot upload guidelines (403 Forbidden)
    def test_02_employee_cannot_upload_guidelines(self, client: TestClient, rbac_fixture):
        ws_id = rbac_fixture["ws_a"].id
        headers = rbac_fixture["headers_employee_a"]

        file_payload = {
            "file": ("unauthorized.txt", io.BytesIO(b"Employee guidelines"), "text/plain")
        }
        res = client.post(f"/api/v1/workspaces/{ws_id}/guidelines/upload", files=file_payload, headers=headers)
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 3. Reviewer cannot upload guidelines (403 Forbidden)
    def test_03_reviewer_cannot_upload_guidelines(self, client: TestClient, rbac_fixture):
        ws_id = rbac_fixture["ws_a"].id
        headers = rbac_fixture["headers_reviewer_a"]

        file_payload = {
            "file": ("reviewer_notes.txt", io.BytesIO(b"Reviewer guidelines"), "text/plain")
        }
        res = client.post(f"/api/v1/workspaces/{ws_id}/guidelines/upload", files=file_payload, headers=headers)
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 4. Admin can approve candidate rules
    def test_04_admin_can_approve_candidate_rules(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        # Create pending candidate rule
        rule = BrandRule(
            workspace_id=ws_id,
            title="Candidate Rule 1",
            description="Always cite source docs",
            category="Compliance",
            approval_status="pending",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        res = client.post(f"/api/v1/rules/{rule.id}/approve", headers=rbac_fixture["headers_admin_a"])
        assert res.status_code == 200
        assert res.json()["approval_status"] == "approved"

    # 5. Employee cannot approve candidate rules (403 Forbidden)
    def test_05_employee_cannot_approve_candidate_rules(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        rule = BrandRule(
            workspace_id=ws_id,
            title="Candidate Rule 2",
            description="Use brand font",
            category="Visual",
            approval_status="pending",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        res = client.post(f"/api/v1/rules/{rule.id}/approve", headers=rbac_fixture["headers_employee_a"])
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 6. Reviewer cannot approve candidate rules (403 Forbidden)
    def test_06_reviewer_cannot_approve_candidate_rules(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        rule = BrandRule(
            workspace_id=ws_id,
            title="Candidate Rule 3",
            description="Logo minimum padding",
            category="Visual",
            approval_status="pending",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        res = client.post(f"/api/v1/rules/{rule.id}/approve", headers=rbac_fixture["headers_reviewer_a"])
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 7. Employee cannot create, edit or delete official rules (403 Forbidden)
    def test_07_employee_cannot_create_edit_or_delete_official_rules(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        headers = rbac_fixture["headers_employee_a"]

        # Create attempt
        res_create = client.post(
            f"/api/v1/workspaces/{ws_id}/rules",
            json={"title": "Emp Rule", "description": "Emp Desc", "category": "Tone"},
            headers=headers,
        )
        assert res_create.status_code == 403

        # Create an official rule via db
        rule = BrandRule(
            workspace_id=ws_id,
            title="Official Rule Alpha",
            description="Existing description",
            category="Brand",
            approval_status="approved",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        # Edit attempt
        res_edit = client.patch(
            f"/api/v1/rules/{rule.id}",
            json={"title": "Hacked Title"},
            headers=headers,
        )
        assert res_edit.status_code == 403

        # Delete attempt
        res_del = client.delete(f"/api/v1/rules/{rule.id}", headers=headers)
        assert res_del.status_code == 403

    # 8. Reviewer cannot create, edit or delete official rules (403 Forbidden)
    def test_08_reviewer_cannot_create_edit_or_delete_official_rules(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        headers = rbac_fixture["headers_reviewer_a"]

        # Create attempt
        res_create = client.post(
            f"/api/v1/workspaces/{ws_id}/rules",
            json={"title": "Rev Rule", "description": "Rev Desc", "category": "Tone"},
            headers=headers,
        )
        assert res_create.status_code == 403

        # Create an official rule via db
        rule = BrandRule(
            workspace_id=ws_id,
            title="Official Rule Beta",
            description="Existing description",
            category="Brand",
            approval_status="approved",
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        # Edit attempt
        res_edit = client.patch(
            f"/api/v1/rules/{rule.id}",
            json={"title": "Rev Altered Title"},
            headers=headers,
        )
        assert res_edit.status_code == 403

        # Delete attempt
        res_del = client.delete(f"/api/v1/rules/{rule.id}", headers=headers)
        assert res_del.status_code == 403

    # 9. Employee cannot approve content reviews (403 Forbidden)
    def test_09_employee_cannot_approve_content_reviews(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        # Create a content review submitted by employee
        review = ContentReview(
            workspace_id=ws_id,
            title="Summer Promotion Draft",
            content="Get instant access today.",
            original_content="Get instant access today.",
            content_type="social_media",
            status="in_review",
            compliance_score=90,
            submitted_by=rbac_fixture["employee_a"].id,
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        # Request approval ticket
        ticket_res = client.post(
            f"/api/v1/reviews/{review.id}/request-approval",
            json={"comment": "Ready for sign-off"},
            headers=rbac_fixture["headers_employee_a"],
        )
        assert ticket_res.status_code in (200, 201)
        ticket_id = ticket_res.json()["id"]

        # Employee self-approval attempt must be 403
        res_approve = client.post(
            f"/api/v1/approvals/{ticket_id}/approve",
            json={"comment": "Self approving"},
            headers=rbac_fixture["headers_employee_a"],
        )
        assert res_approve.status_code == 403
        assert "Reviewer or Admin" in res_approve.json()["detail"]

    # 10. Reviewer can approve submitted content (200 OK)
    def test_10_reviewer_can_approve_submitted_content(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        review = ContentReview(
            workspace_id=ws_id,
            title="Q3 Newsletter",
            content="Educational newsletter text.",
            original_content="Educational newsletter text.",
            content_type="newsletter",
            status="in_review",
            compliance_score=95,
            submitted_by=rbac_fixture["employee_a"].id,
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        ticket_res = client.post(
            f"/api/v1/reviews/{review.id}/request-approval",
            json={"comment": "Please review"},
            headers=rbac_fixture["headers_employee_a"],
        )
        assert ticket_res.status_code in (200, 201)
        ticket_id = ticket_res.json()["id"]

        # Reviewer approves content ticket
        res_approve = client.post(
            f"/api/v1/approvals/{ticket_id}/approve",
            json={"comment": "Looks compliant and meets guidelines."},
            headers=rbac_fixture["headers_reviewer_a"],
        )
        assert res_approve.status_code == 200
        assert res_approve.json()["status"] == "approved"

    # 11. Employee cannot manage memberships (403 Forbidden)
    def test_11_employee_cannot_manage_memberships(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        new_u = make_user(db, "outsider11@example.com", "Outsider 11")

        res = client.post(
            f"/api/v1/workspaces/{ws_id}/members",
            json={"user_id": new_u.id, "role": "Employee"},
            headers=rbac_fixture["headers_employee_a"],
        )
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 12. Reviewer cannot manage memberships (403 Forbidden)
    def test_12_reviewer_cannot_manage_memberships(self, client: TestClient, rbac_fixture, db: Session):
        ws_id = rbac_fixture["ws_a"].id
        new_u = make_user(db, "outsider12@example.com", "Outsider 12")

        res = client.post(
            f"/api/v1/workspaces/{ws_id}/members",
            json={"user_id": new_u.id, "role": "Employee"},
            headers=rbac_fixture["headers_reviewer_a"],
        )
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 13. Employee cannot change roles (403 Forbidden)
    def test_13_employee_cannot_change_roles(self, client: TestClient, rbac_fixture):
        ws_id = rbac_fixture["ws_a"].id
        target_uid = rbac_fixture["reviewer_a"].id

        res = client.patch(
            f"/api/v1/workspaces/{ws_id}/members/{target_uid}/role",
            json={"role": "Admin"},
            headers=rbac_fixture["headers_employee_a"],
        )
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 14. Reviewer cannot change roles (403 Forbidden)
    def test_14_reviewer_cannot_change_roles(self, client: TestClient, rbac_fixture):
        ws_id = rbac_fixture["ws_a"].id
        target_uid = rbac_fixture["employee_a"].id

        res = client.patch(
            f"/api/v1/workspaces/{ws_id}/members/{target_uid}/role",
            json={"role": "Admin"},
            headers=rbac_fixture["headers_reviewer_a"],
        )
        assert res.status_code == 403
        assert "Required workspace role: Admin" in res.json()["detail"]

    # 15. Admin can manage membership requests (approve/reject join requests)
    def test_15_admin_can_manage_membership_requests(self, client: TestClient, rbac_fixture, db: Session):
        ws = rbac_fixture["ws_a"]
        admin_headers = rbac_fixture["headers_admin_a"]

        applicant1 = make_user(db, "applicant_approve@example.com", "Applicant Approve")
        applicant2 = make_user(db, "applicant_reject@example.com", "Applicant Reject")

        # Submit join requests
        workspace_service.request_join(db, org_id=ws.org_id, user_id=applicant1.id)
        workspace_service.request_join(db, org_id=ws.org_id, user_id=applicant2.id)

        # Admin lists pending requests
        list_res = client.get(f"/api/v1/workspaces/{ws.id}/join-requests", headers=admin_headers)
        assert list_res.status_code == 200
        req_uids = [r["user_id"] for r in list_res.json()]
        assert applicant1.id in req_uids
        assert applicant2.id in req_uids

        # Admin approves applicant 1
        app_res = client.post(
            f"/api/v1/workspaces/{ws.id}/join-requests/{applicant1.id}/approve",
            headers=admin_headers,
        )
        assert app_res.status_code == 200
        assert app_res.json()["status"] == "approved"
        assert app_res.json()["role"] == "Employee"

        # Admin rejects applicant 2
        rej_res = client.post(
            f"/api/v1/workspaces/{ws.id}/join-requests/{applicant2.id}/reject",
            headers=admin_headers,
        )
        assert rej_res.status_code == 200
        assert rej_res.json()["success"] is True

        # Verify applicant 1 is now an approved member and applicant 2 is removed
        mem1 = workspace_service.get_member(db, ws.id, applicant1.id)
        assert mem1 is not None and mem1.status == "approved"

        mem2 = workspace_service.get_member(db, ws.id, applicant2.id)
        assert mem2 is None

    # 16. Cross-tenant access remains blocked
    def test_16_cross_tenant_access_remains_blocked(self, client: TestClient, rbac_fixture, db: Session):
        ws_b = rbac_fixture["ws_b"]
        headers_a = rbac_fixture["headers_employee_a"]

        # Create resource in Org B
        review_b = ContentReview(
            workspace_id=ws_b.id,
            title="Confidential Org B Campaign",
            content="Classified financial copy.",
            original_content="Classified financial copy.",
            content_type="social_media",
            status="in_review",
            compliance_score=99,
            submitted_by=rbac_fixture["employee_b"].id,
        )
        rule_b = BrandRule(
            workspace_id=ws_b.id,
            title="Org B Exclusive Rule",
            description="Classified rule",
            category="Legal",
            approval_status="approved",
        )
        db.add_all([review_b, rule_b])
        db.commit()

        # Employee from Org A tries to access Org B workspace details
        assert client.get(f"/api/v1/workspaces/{ws_b.id}", headers=headers_a).status_code == 403

        # Employee from Org A tries to access Org B members
        assert client.get(f"/api/v1/workspaces/{ws_b.id}/members", headers=headers_a).status_code == 403

        # Employee from Org A tries to access Org B rules
        assert client.get(f"/api/v1/workspaces/{ws_b.id}/rules", headers=headers_a).status_code == 403

        # Employee from Org A tries to access Org B guidelines
        assert client.get(f"/api/v1/workspaces/{ws_b.id}/guidelines", headers=headers_a).status_code == 403

        # Employee from Org A tries to access Org B review by ID
        assert client.get(f"/api/history/{review_b.id}", headers=headers_a).status_code == 403

    # 17. Unauthenticated user has zero access
    def test_17_unauthenticated_user_rejected(self, client: TestClient, rbac_fixture):
        ws_a = rbac_fixture["ws_a"]
        # No authorization headers provided
        assert client.get(f"/api/v1/workspaces").status_code == 401
        assert client.get(f"/api/v1/workspaces/{ws_a.id}").status_code == 401
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/rules").status_code == 401
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/guidelines").status_code == 401

    # 18. Authenticated user with unresolved membership has zero permissions
    def test_18_authenticated_user_unresolved_membership_has_zero_permissions(
        self, client: TestClient, rbac_fixture, db: Session
    ):
        outsider = make_user(db, "unresolved_outsider@example.com", "Unresolved Outsider")
        outsider_headers = make_auth_header(outsider)
        ws_a = rbac_fixture["ws_a"]

        # Outsider's workspace list does not include ws_a
        res = client.get("/api/v1/workspaces", headers=outsider_headers)
        assert res.status_code == 200
        assert not any(w["id"] == ws_a.id for w in res.json())

        # Direct access to ws_a returns 403 Forbidden
        assert client.get(f"/api/v1/workspaces/{ws_a.id}", headers=outsider_headers).status_code == 403
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/rules", headers=outsider_headers).status_code == 403
        assert client.post(f"/api/v1/workspaces/{ws_a.id}/rules", json={"title": "R", "description": "D", "category": "Legal"}, headers=outsider_headers).status_code == 403
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/guidelines", headers=outsider_headers).status_code == 403

    # 19. Pending membership has zero permissions
    def test_19_pending_membership_has_zero_permissions(
        self, client: TestClient, rbac_fixture, db: Session
    ):
        applicant = make_user(db, "pending_applicant@example.com", "Pending Applicant")
        applicant_headers = make_auth_header(applicant)
        ws_a = rbac_fixture["ws_a"]

        # Create explicit pending join request
        member = WorkspaceMember(
            workspace_id=ws_a.id,
            user_id=applicant.id,
            role="Employee",
            status="pending",
        )
        db.add(member)
        db.commit()

        # Pending user does NOT see ws_a in approved workspaces
        res = client.get("/api/v1/workspaces", headers=applicant_headers)
        assert res.status_code == 200
        assert not any(w["id"] == ws_a.id for w in res.json())

        # Accessing ws_a directly is strictly blocked (403)
        assert client.get(f"/api/v1/workspaces/{ws_a.id}", headers=applicant_headers).status_code == 403
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/rules", headers=applicant_headers).status_code == 403
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/guidelines", headers=applicant_headers).status_code == 403

    # 20. Approved Employee has employee permissions only (no admin/reviewer elevation)
    def test_20_approved_employee_has_employee_permissions_only(
        self, client: TestClient, rbac_fixture
    ):
        ws_a = rbac_fixture["ws_a"]
        emp_headers = rbac_fixture["headers_employee_a"]

        # Employee can read approved rules
        rules_res = client.get(f"/api/v1/workspaces/{ws_a.id}/rules", headers=emp_headers)
        assert rules_res.status_code == 200

        # Employee CANNOT view pending candidate rules (Admin only)
        assert client.get(f"/api/v1/workspaces/{ws_a.id}/rules/pending", headers=emp_headers).status_code == 403

        # Employee CANNOT create official rules
        assert client.post(
            f"/api/v1/workspaces/{ws_a.id}/rules",
            json={"title": "Unauthorized Rule", "description": "Desc", "category": "Legal"},
            headers=emp_headers,
        ).status_code == 403

        # Employee CANNOT upload guidelines
        assert client.post(
            f"/api/v1/workspaces/{ws_a.id}/guidelines/upload",
            files={"file": ("test.txt", io.BytesIO(b"Data"), "text/plain")},
            headers=emp_headers,
        ).status_code == 403

    # 21. Approved Admin has full governance permissions
    def test_21_approved_admin_has_full_governance_permissions(
        self, client: TestClient, rbac_fixture
    ):
        ws_a = rbac_fixture["ws_a"]
        admin_headers = rbac_fixture["headers_admin_a"]

        # Admin can create rules
        rule_res = client.post(
            f"/api/v1/workspaces/{ws_a.id}/rules",
            json={"title": "Official Rule By Admin", "description": "Strict compliance rule.", "category": "Legal"},
            headers=admin_headers,
        )
        assert rule_res.status_code == 201
        created_rule_id = rule_res.json()["id"]

        # Admin can edit rules
        patch_res = client.patch(
            f"/api/v1/rules/{created_rule_id}",
            json={"title": "Updated Official Rule By Admin"},
            headers=admin_headers,
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["title"] == "Updated Official Rule By Admin"

        # Admin can delete rules
        del_res = client.delete(f"/api/v1/rules/{created_rule_id}", headers=admin_headers)
        assert del_res.status_code == 204

    # 22. Switching from Admin to Employee workspace enforces isolated roles
    def test_22_switching_workspaces_between_admin_and_employee_enforces_isolated_roles(
        self, client: TestClient, rbac_fixture, db: Session
    ):
        ws_a = rbac_fixture["ws_a"]  # User is Admin here
        ws_b = rbac_fixture["ws_b"]  # User will be Employee here
        dual_user = make_user(db, "dual_role_user@example.com", "Dual Role User")
        dual_headers = make_auth_header(dual_user)

        # Assign Admin in ws_a, Employee in ws_b
        workspace_service.add_member(db, ws_a.id, dual_user.id, role="Admin")
        workspace_service.add_member(db, ws_b.id, dual_user.id, role="Employee")

        # In ws_a, user can create brand rules
        res_a = client.post(
            f"/api/v1/workspaces/{ws_a.id}/rules",
            json={"title": "Rule in Org A", "description": "Desc", "category": "Voice"},
            headers=dual_headers,
        )
        assert res_a.status_code == 201

        # In ws_b, user is strictly Employee -> creating rules is blocked (403)
        res_b = client.post(
            f"/api/v1/workspaces/{ws_b.id}/rules",
            json={"title": "Rule in Org B", "description": "Desc", "category": "Voice"},
            headers=dual_headers,
        )
        assert res_b.status_code == 403
        assert "Required workspace role: Admin" in res_b.json()["detail"]
