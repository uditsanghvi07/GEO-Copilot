"""Smoke tests for the auth scaffold: register, login, and /auth/me."""


def test_register_returns_jwt(client):
    response = client.post(
        "/auth/register", json={"email": "founder@example.com", "password": "supersecret1"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 0


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "supersecret1"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409


def test_login_with_correct_credentials_returns_jwt(client):
    client.post("/auth/register", json={"email": "login@example.com", "password": "supersecret1"})

    response = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "supersecret1"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_wrong_password_rejected(client):
    client.post("/auth/register", json={"email": "wrong@example.com", "password": "supersecret1"})

    response = client.post(
        "/auth/login", json={"email": "wrong@example.com", "password": "not-the-password"}
    )
    assert response.status_code == 401


def test_me_requires_valid_token(client):
    register_response = client.post(
        "/auth/register", json={"email": "me@example.com", "password": "supersecret1"}
    )
    token = register_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_me_rejects_missing_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
