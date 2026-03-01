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
