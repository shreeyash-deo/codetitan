def test_register_user_success(client):
    payload = {
        "name": "Marcus Vance",
        "email": "marcus@novapay.io",
        "password": "SecurePassword123!",
        "role": "Reviewer",  # Client-supplied role must be ignored
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Marcus Vance"
    assert data["email"] == "marcus@novapay.io"
    assert data["role"] == "User"
    assert "id" in data
    assert "hashed_password" not in data


def test_registration_cannot_self_assign_admin_or_reviewer(client):
    for i, privileged_role in enumerate(["Admin", "Reviewer", "admin", "SUPERADMIN"]):
        res = client.post(
            "/api/auth/register",
            json={
                "name": f"Hacker {privileged_role}",
                "email": f"hacker_{i}_{privileged_role.lower()}@corp.io",
                "password": "Password123!",
                "role": privileged_role,
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["role"] == "User"


def test_register_duplicate_email_fails(client, test_user):
    payload = {
        "name": "Another User",
        "email": test_user.email,
        "password": "Password123!",
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_login_success(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "ValidPassword123!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_password_fails(client, test_user):
    payload = {
        "email": test_user.email,
        "password": "WrongPassword!",
    }
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_get_current_user_me(client, auth_headers, test_user):
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == test_user.id
    assert data["role"] == test_user.role


def test_get_current_user_unauthorized(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
