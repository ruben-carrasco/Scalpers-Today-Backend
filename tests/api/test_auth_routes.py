def test_login_invalid_credentials(client):
    # Try to login with non-existent user
    payload = {"email": "wrong@example.com", "password": "wrongpassword"}
    response = client.post("/api/v1/auth/login", json=payload)
    # Since we are using the real container (but with an empty dev db or whatever settings),
    # it should return 401 if user doesn't exist
    assert response.status_code in [401, 404]


def test_register_new_user(client):
    import uuid

    random_email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "email": random_email,
        "password": "strongPassword123",
        "name": "Test User",
        "language": "es",
        "currency": "eur",
        "timezone": "Europe/Madrid",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == random_email
    assert "access_token" in data["token"]


def test_register_duplicate_user(client):
    import uuid

    email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
    payload = {"email": email, "password": "strongPassword123", "name": "Test User"}
    # First time
    client.post("/api/v1/auth/register", json=payload)
    # Second time
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409  # Conflict
    assert "already registered" in response.json()["detail"]["message"].lower()


def test_password_reset_request_is_generic_for_unknown_email(client):
    import uuid

    email = f"missing_{uuid.uuid4().hex[:6]}@example.com"

    response = client.post("/api/v1/auth/password-reset/request", json={"email": email})

    assert response.status_code == 200
    data = response.json()
    assert "If an account exists" in data["message"]
    assert data["reset_token"] is None


def test_password_reset_flow_allows_login_with_new_password(client):
    import uuid

    email = f"reset_{uuid.uuid4().hex[:6]}@example.com"
    old_password = "strongPassword123"
    new_password = "newStrongPassword123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": old_password, "name": "Reset User"},
    )
    assert register_response.status_code == 201

    request_response = client.post("/api/v1/auth/password-reset/request", json={"email": email})
    assert request_response.status_code == 200
    reset_token = request_response.json()["reset_token"]
    assert reset_token

    confirm_response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": reset_token, "new_password": new_password},
    )
    assert confirm_response.status_code == 200

    old_login_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": old_password}
    )
    assert old_login_response.status_code == 401

    new_login_response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": new_password}
    )
    assert new_login_response.status_code == 200
