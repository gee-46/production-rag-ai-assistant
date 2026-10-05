def test_register_login_and_me_flow(client):
    resp = client.post(
        "/auth/register", json={"email": "reg@example.com", "password": "password123", "full_name": "Reg User"}
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "reg@example.com"

    resp = client.post("/auth/login", json={"email": "reg@example.com", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_duplicate_registration_is_rejected(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_wrong_password_is_rejected(client):
    client.post("/auth/register", json={"email": "wp@example.com", "password": "password123"})
    resp = client.post("/auth/login", json={"email": "wp@example.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_unauthenticated_request_is_rejected(client):
    resp = client.get("/workspaces")
    assert resp.status_code == 401


def test_create_and_list_workspace(client, registered_user):
    resp = client.post("/workspaces", json={"name": "My WS"}, headers=registered_user["headers"])
    assert resp.status_code == 201
    resp = client.get("/workspaces", headers=registered_user["headers"])
    assert resp.status_code == 200
    assert any(w["name"] == "My WS" for w in resp.json())


def test_non_member_cannot_access_workspace(client, registered_user, workspace):
    client.post("/auth/register", json={"email": "outsider@example.com", "password": "password123"})
    outsider_token = client.post(
        "/auth/login", json={"email": "outsider@example.com", "password": "password123"}
    ).json()["access_token"]

    resp = client.get(
        f"/workspaces/{workspace['id']}/documents", headers={"Authorization": f"Bearer {outsider_token}"}
    )
    assert resp.status_code == 403
