import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.services.auth_service import auth_service
from app.services.workspace_service import workspace_service
from app.schemas.user import UserCreate
from app.core.security import create_access_token


def make_auth_header(user: User) -> dict:
    token = create_access_token(
        subject=user.id,
        extra_claims={"role": user.role, "email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}


def make_user(db: Session, email: str, name: str = "Test User") -> User:
    return auth_service.create_user(
        db,
        UserCreate(name=name, email=email, password="Password123!"),
    )


class TestOrganisationJoiningWorkflow:
    """Comprehensive test suite for the 14 organization joining & onboarding scenarios."""

    def test_01_existing_admin_retains_access(self, client: TestClient, db: Session):
        """1. Existing Admin retains access with status='approved'."""
        admin = make_user(db, email="admin1@test.com", name="Admin One")
        ws = workspace_service.create_workspace(db, name="Org Alpha", creator_id=admin.id)
        headers = make_auth_header(admin)

        # Check membership is approved
        member = workspace_service.get_member(db, ws.id, admin.id)
        assert member is not None
        assert member.role == "Admin"
        assert member.status == "approved"

        # Admin accesses workspace details & members
        res = client.get(f"/api/v1/workspaces/{ws.id}", headers=headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Org Alpha"

        res_members = client.get(f"/api/v1/workspaces/{ws.id}/members", headers=headers)
        assert res_members.status_code == 200
        assert len(res_members.json()) == 1

    def test_02_new_admin_creates_organisation(self, client: TestClient, db: Session):
        """2. New Admin registers and creates an organisation with valid ORG ID."""
        reg_payload = {
            "name": "Acme Admin",
            "email": "acme.admin@example.com",
            "password": "Password123!",
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201

        user = auth_service.get_by_email(db, "acme.admin@example.com")
        headers = make_auth_header(user)

        # Create workspace as admin
        res_create = client.post("/api/v1/workspaces", json={"name": "Acme Corp"}, headers=headers)
        assert res_create.status_code == 201
        created_ws = res_create.json()
        assert created_ws["org_id"].startswith("ORG-")

        # Verify membership status is approved and role is Admin
        member = workspace_service.get_member(db, created_ws["id"], user.id)
        assert member.status == "approved"
        assert member.role == "Admin"

    def test_03_new_employee_requests_membership_via_registration(self, client: TestClient, db: Session):
        """3. New Employee registers with an existing ORG ID; enters pending status."""
        admin = make_user(db, email="admin3@test.com", name="Admin Three")
        ws = workspace_service.create_workspace(db, name="Beta Corp", creator_id=admin.id)

        reg_payload = {
            "name": "Jane Employee",
            "email": "jane@betacorp.com",
            "password": "Password123!",
            "org_id": ws.org_id,
        }
        res = client.post("/api/v1/auth/register", json=reg_payload)
        assert res.status_code == 201

        employee = auth_service.get_by_email(db, "jane@betacorp.com")
        emp_headers = make_auth_header(employee)

        # Has NO approved workspaces
        res_ws = client.get("/api/v1/workspaces", headers=emp_headers)
        assert res_ws.status_code == 200
        assert len(res_ws.json()) == 0

        # Listed in user pending requests
        res_pending = client.get("/api/v1/workspaces/pending-requests", headers=emp_headers)
        assert res_pending.status_code == 200
        pending_data = res_pending.json()
        assert len(pending_data) == 1
        assert pending_data[0]["org_id"] == ws.org_id
        assert pending_data[0]["status"] == "pending"
        assert pending_data[0]["role"] == "Employee"

    def test_04_existing_user_joins_without_reregistering(self, client: TestClient, db: Session):
        """4. Existing registered user submits a join request via POST /api/v1/workspaces/join."""
        admin = make_user(db, email="admin4@test.com", name="Admin Four")
        ws = workspace_service.create_workspace(db, name="Gamma Inc", creator_id=admin.id)

        user = make_user(db, email="mark@freelance.com", name="Mark Joiner")
        headers = make_auth_header(user)

        res = client.post("/api/v1/workspaces/join", json={"org_id": ws.org_id}, headers=headers)
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["status"] == "pending"
        assert data["role"] == "Employee"
        assert data["workspace_id"] == ws.id

    def test_05_invalid_org_id_is_rejected(self, client: TestClient, db: Session):
        """5. Invalid ORG ID is rejected with 404."""
        user = make_user(db, email="user5@test.com", name="User Five")
        headers = make_auth_header(user)

        res = client.post("/api/v1/workspaces/join", json={"org_id": "ORG-INVALID99"}, headers=headers)
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

        # Registration with invalid ORG ID
        reg_payload = {
            "name": "Bad Org User",
            "email": "bad@example.com",
            "password": "Password123!",
            "org_id": "ORG-FAKEXXXX",
        }
        res_reg = client.post("/api/v1/auth/register", json=reg_payload)
        assert res_reg.status_code == 404

    def test_06_duplicate_join_request_is_rejected(self, client: TestClient, db: Session):
        """6. Duplicate join request is rejected with HTTP 400."""
        admin = make_user(db, email="admin6@test.com", name="Admin Six")
        ws = workspace_service.create_workspace(db, name="Delta Ltd", creator_id=admin.id)

        user = make_user(db, email="dup@test.com", name="Dup User")
        headers = make_auth_header(user)

        # First request succeeds
        res1 = client.post("/api/v1/workspaces/join", json={"org_id": ws.org_id}, headers=headers)
        assert res1.status_code in (200, 201)

        # Second request fails
        res2 = client.post("/api/v1/workspaces/join", json={"org_id": ws.org_id}, headers=headers)
        assert res2.status_code == 400
        assert "pending membership request" in res2.json()["detail"].lower()

    def test_07_pending_member_cannot_access_workspace_data(self, client: TestClient, db: Session):
        """7. Pending member cannot access workspace-protected data (403 Forbidden)."""
        admin = make_user(db, email="admin7@test.com", name="Admin Seven")
        ws = workspace_service.create_workspace(db, name="Epsilon Co", creator_id=admin.id)

        user = make_user(db, email="pending7@test.com", name="Pending User")
        workspace_service.request_join(db, org_id=ws.org_id, user_id=user.id)
        emp_headers = make_auth_header(user)

        # Workspace details: 403
        res = client.get(f"/api/v1/workspaces/{ws.id}", headers=emp_headers)
        assert res.status_code == 403

        # Workspace rules: 403
        res_rules = client.get(f"/api/v1/workspaces/{ws.id}/rules", headers=emp_headers)
        assert res_rules.status_code == 403

        # Compat /brands: returns [] without auto-generating a default workspace
        res_brands = client.get("/api/v1/brands", headers=emp_headers)
        assert res_brands.status_code == 200
        assert res_brands.json() == []

    def test_08_admin_approves_membership_request(self, client: TestClient, db: Session):
        """8. Admin approves membership request; status transitions to approved with role Employee."""
        admin = make_user(db, email="admin8@test.com", name="Admin Eight")
        ws = workspace_service.create_workspace(db, name="Zeta Tech", creator_id=admin.id)
        admin_headers = make_auth_header(admin)

        user = make_user(db, email="applicant8@test.com", name="Applicant Eight")
        workspace_service.request_join(db, org_id=ws.org_id, user_id=user.id)

        # Admin lists pending requests
        res_list = client.get(f"/api/v1/workspaces/{ws.id}/join-requests", headers=admin_headers)
        assert res_list.status_code == 200
        reqs = res_list.json()
        assert len(reqs) == 1
        assert reqs[0]["user_id"] == user.id

        # Admin approves
        res_app = client.post(
            f"/api/v1/workspaces/{ws.id}/join-requests/{user.id}/approve", headers=admin_headers
        )
        assert res_app.status_code == 200
        assert res_app.json()["status"] == "approved"
        assert res_app.json()["role"] == "Employee"

        # Pending queue is now empty
        res_list_after = client.get(f"/api/v1/workspaces/{ws.id}/join-requests", headers=admin_headers)
        assert len(res_list_after.json()) == 0

    def test_09_approved_employee_accesses_permitted_resources(self, client: TestClient, db: Session):
        """9. Approved Employee can list organisation and access permitted resources."""
        admin = make_user(db, email="admin9@test.com", name="Admin Nine")
        ws = workspace_service.create_workspace(db, name="Eta Systems", creator_id=admin.id)

        user = make_user(db, email="emp9@test.com", name="Emp Nine")
        workspace_service.request_join(db, org_id=ws.org_id, user_id=user.id)
        workspace_service.approve_request(db, ws.id, user.id, admin_user=admin)

        emp_headers = make_auth_header(user)

        # Now shows up in workspaces
        res_ws = client.get("/api/v1/workspaces", headers=emp_headers)
        assert res_ws.status_code == 200
        assert len(res_ws.json()) == 1
        assert res_ws.json()[0]["id"] == ws.id

        # Workspace details
        res_details = client.get(f"/api/v1/workspaces/{ws.id}", headers=emp_headers)
        assert res_details.status_code == 200

        # Rules listing succeeds
        res_rules = client.get(f"/api/v1/workspaces/{ws.id}/rules", headers=emp_headers)
        assert res_rules.status_code == 200

    def test_10_admin_promotes_employee_to_reviewer_and_demotes(self, client: TestClient, db: Session):
        """10. Admin promotes Employee to Reviewer and demotes Reviewer back to Employee."""
        admin = make_user(db, email="admin10@test.com", name="Admin Ten")
        ws = workspace_service.create_workspace(db, name="Theta Labs", creator_id=admin.id)
        admin_headers = make_auth_header(admin)

        user = make_user(db, email="emp10@test.com", name="Emp Ten")
        workspace_service.add_member(db, ws.id, user.id, role="Employee")

        # Promote to Reviewer
        res_prom = client.patch(
            f"/api/v1/workspaces/{ws.id}/members/{user.id}/role",
            json={"role": "Reviewer"},
            headers=admin_headers,
        )
        assert res_prom.status_code == 200
        assert res_prom.json()["role"] == "Reviewer"

        # Demote back to Employee
        res_dem = client.patch(
            f"/api/v1/workspaces/{ws.id}/members/{user.id}/role",
            json={"role": "Employee"},
            headers=admin_headers,
        )
        assert res_dem.status_code == 200
        assert res_dem.json()["role"] == "Employee"

        # Admin attempting to modify their own role fails
        res_self = client.patch(
            f"/api/v1/workspaces/{ws.id}/members/{admin.id}/role",
            json={"role": "Reviewer"},
            headers=admin_headers,
        )
        assert res_self.status_code == 400
        assert "cannot change their own role" in res_self.json()["detail"].lower()

    def test_11_employee_cannot_self_assign_reviewer_or_admin(self, client: TestClient, db: Session):
        """11. Employee cannot self-assign role (403 Forbidden)."""
        admin = make_user(db, email="admin11@test.com", name="Admin Eleven")
        ws = workspace_service.create_workspace(db, name="Iota Group", creator_id=admin.id)

        user = make_user(db, email="emp11@test.com", name="Emp Eleven")
        workspace_service.add_member(db, ws.id, user.id, role="Employee")
        emp_headers = make_auth_header(user)

        res = client.patch(
            f"/api/v1/workspaces/{ws.id}/members/{user.id}/role",
            json={"role": "Admin"},
            headers=emp_headers,
        )
        assert res.status_code == 403

    def test_12_employee_cannot_approve_join_requests(self, client: TestClient, db: Session):
        """12. Employee cannot approve join requests (403 Forbidden)."""
        admin = make_user(db, email="admin12@test.com", name="Admin Twelve")
        ws = workspace_service.create_workspace(db, name="Kappa Holdings", creator_id=admin.id)

        emp = make_user(db, email="emp12@test.com", name="Emp Twelve")
        workspace_service.add_member(db, ws.id, emp.id, role="Employee")

        applicant = make_user(db, email="app12@test.com", name="App Twelve")
        workspace_service.request_join(db, org_id=ws.org_id, user_id=applicant.id)

        emp_headers = make_auth_header(emp)

        # Attempt to list requests -> 403
        res_list = client.get(f"/api/v1/workspaces/{ws.id}/join-requests", headers=emp_headers)
        assert res_list.status_code == 403

        # Attempt to approve -> 403
        res_app = client.post(
            f"/api/v1/workspaces/{ws.id}/join-requests/{applicant.id}/approve", headers=emp_headers
        )
        assert res_app.status_code == 403

    def test_13_rejected_user_record_is_deleted_and_can_reapply(self, client: TestClient, db: Session):
        """13. Rejected user record is deleted; user can re-apply."""
        admin = make_user(db, email="admin13@test.com", name="Admin Thirteen")
        ws = workspace_service.create_workspace(db, name="Lambda Media", creator_id=admin.id)
        admin_headers = make_auth_header(admin)

        user = make_user(db, email="user13@test.com", name="User Thirteen")
        workspace_service.request_join(db, org_id=ws.org_id, user_id=user.id)
        user_headers = make_auth_header(user)

        # Admin rejects
        res_rej = client.post(
            f"/api/v1/workspaces/{ws.id}/join-requests/{user.id}/reject", headers=admin_headers
        )
        assert res_rej.status_code == 200

        # Membership row is deleted
        member = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id)
            .first()
        )
        assert member is None

        # User re-applies successfully
        res_reapply = client.post("/api/v1/workspaces/join", json={"org_id": ws.org_id}, headers=user_headers)
        assert res_reapply.status_code in (200, 201)
        assert res_reapply.json()["status"] == "pending"

        # User cancels their own request
        res_cancel = client.delete(f"/api/v1/workspaces/pending-requests/{ws.id}", headers=user_headers)
        assert res_cancel.status_code == 200

        member_after_cancel = (
            db.query(WorkspaceMember)
            .filter(WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user.id)
            .first()
        )
        assert member_after_cancel is None

    def test_14_cross_tenant_isolation_remains_intact(self, client: TestClient, db: Session):
        """14. Cross-tenant isolation remains strictly enforced across organisations."""
        admin_a = make_user(db, email="admin_a@tenant.com", name="Admin A")
        ws_a = workspace_service.create_workspace(db, name="Tenant A Org", creator_id=admin_a.id)

        admin_b = make_user(db, email="admin_b@tenant.com", name="Admin B")
        ws_b = workspace_service.create_workspace(db, name="Tenant B Org", creator_id=admin_b.id)

        headers_a = make_auth_header(admin_a)

        # Admin A cannot access Org B details
        res_ws = client.get(f"/api/v1/workspaces/{ws_b.id}", headers=headers_a)
        assert res_ws.status_code == 403

        # Admin A cannot view or approve Org B join requests
        res_req = client.get(f"/api/v1/workspaces/{ws_b.id}/join-requests", headers=headers_a)
        assert res_req.status_code == 403
