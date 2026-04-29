import pytest
import uuid


@pytest.fixture
def user_a(client):
    email = f"user_a_{uuid.uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Password123!", "name": "User A"}
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = resp.json()["token"]["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "id": resp.json()["user"]["id"]}


@pytest.fixture
def user_b(client):
    email = f"user_b_{uuid.uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register", json={"email": email, "password": "Password123!", "name": "User B"}
    )
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = resp.json()["token"]["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "id": resp.json()["user"]["id"]}


def test_cannot_access_other_user_alert(client, user_a, user_b):
    # User A creates an alert
    payload = {
        "name": "User A Alert",
        "description": "Private",
        "conditions": [{"alert_type": "high_impact_event", "value": None}],
        "push_enabled": True,
    }
    resp_a = client.post("/api/v1/alerts", json=payload, headers=user_a["headers"])
    alert_id = resp_a.json()["id"]

    # User B tries to GET it
    resp_b = client.get(f"/api/v1/alerts/{alert_id}", headers=user_b["headers"])
    assert resp_b.status_code == 403
    assert "permission" in resp_b.json()["detail"]


def test_cannot_update_other_user_alert(client, user_a, user_b):
    # User A creates an alert
    payload = {
        "name": "User A Alert",
        "description": "Private",
        "conditions": [{"alert_type": "high_impact_event", "value": None}],
        "push_enabled": True,
    }
    resp_a = client.post("/api/v1/alerts", json=payload, headers=user_a["headers"])
    alert_id = resp_a.json()["id"]

    # User B tries to UPDATE it
    update_payload = {"name": "Hacked", "push_enabled": False}
    resp_b = client.put(
        f"/api/v1/alerts/{alert_id}", json=update_payload, headers=user_b["headers"]
    )
    assert resp_b.status_code in [403, 404]


def test_cannot_delete_other_user_alert(client, user_a, user_b):
    # User A creates an alert
    payload = {
        "name": "User A Alert",
        "description": "Private",
        "conditions": [{"alert_type": "high_impact_event", "value": None}],
        "push_enabled": True,
    }
    resp_a = client.post("/api/v1/alerts", json=payload, headers=user_a["headers"])
    alert_id = resp_a.json()["id"]

    # User B tries to DELETE it
    resp_b = client.delete(f"/api/v1/alerts/{alert_id}", headers=user_b["headers"])
    assert resp_b.status_code in [403, 404]


def test_get_non_existent_alert(client, user_a):
    resp = client.get("/api/v1/alerts/non-existent-id", headers=user_a["headers"])
    assert resp.status_code == 404
