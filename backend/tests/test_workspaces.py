from app.services.auth_service import auth_service
from app.schemas.user import UserCreate
from app.core.security import create_access_token


def test_create_workspace(client, auth_headers):
    payload = {"name": "NovaPay Main"}
    response = client.post("/api/workspaces", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "NovaPay Main"
    assert "id" in data


def test_list_workspaces(client, auth_headers):
    # Create two workspaces
    client.post("/api/workspaces", json={"name": "Workspace A"}, headers=auth_headers)
    client.post("/api/workspaces", json={"name": "Workspace B"}, headers=auth_headers)

    response = client.get("/api/workspaces", headers=auth_headers)
    assert response.status_code == 200
    workspaces = response.json()
    assert len(workspaces) >= 2


def test_get_workspace_by_id(client, auth_headers):
    create_resp = client.post("/api/workspaces", json={"name": "Acme Brand"}, headers=auth_headers)
    ws_id = create_resp.json()["id"]

    response = client.get(f"/api/workspaces/{ws_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ws_id
    assert data["name"] == "Acme Brand"


def test_workspace_access_denied_for_non_member(client, db):
    # Create an editor user who is NOT a member of the workspace
    non_member = auth_service.create_user(
        db,
        UserCreate(name="External User", email="external@other.io", password="Password123!", role="Editor"),
    )
    non_member_token = create_access_token(subject=non_member.id, extra_claims={"role": "Editor", "email": non_member.email})
    non_member_headers = {"Authorization": f"Bearer {non_member_token}"}

    # Create workspace with an admin user
    admin_user = auth_service.create_user(
        db,
        UserCreate(name="Owner User", email="owner@corp.io", password="Password123!", role="Editor"),
    )
    admin_token = create_access_token(subject=admin_user.id, extra_claims={"role": "Editor", "email": admin_user.email})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = client.post("/api/workspaces", json={"name": "Private Workspace"}, headers=admin_headers)
    ws_id = create_resp.json()["id"]

    # Non-member attempts to read workspace details
    forbidden_resp = client.get(f"/api/workspaces/{ws_id}", headers=non_member_headers)
    assert forbidden_resp.status_code == 403
    assert "Access denied" in forbidden_resp.json()["detail"]


def test_add_workspace_member(client, auth_headers, db):
    # Create target colleague to invite
    colleague = auth_service.create_user(
        db,
        UserCreate(name="Elena Rostova", email="elena@novapay.io", password="Password123!", role="Editor"),
    )

    create_resp = client.post("/api/workspaces", json={"name": "Design Workspace"}, headers=auth_headers)
    ws_id = create_resp.json()["id"]

    # Add member
    add_resp = client.post(
        f"/api/workspaces/{ws_id}/members",
        json={"user_id": colleague.id, "role": "Reviewer"},
        headers=auth_headers,
    )
    assert add_resp.status_code == 201
    member_data = add_resp.json()
    assert member_data["workspace_id"] == ws_id
    assert member_data["user_id"] == colleague.id
    assert member_data["role"] == "Reviewer"
