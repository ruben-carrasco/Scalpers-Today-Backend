import pytest

def test_protected_route_without_token(client):
    # alerts is a protected route
    response = client.get("/api/v1/alerts")
    assert response.status_code == 401

def test_protected_route_with_invalid_token(client):
    headers = {"Authorization": "Bearer invalid-token"}
    response = client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 401

def test_protected_route_with_expired_or_malformed_token(client):
    # Just a malformed one
    headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.invalid"}
    response = client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 401
