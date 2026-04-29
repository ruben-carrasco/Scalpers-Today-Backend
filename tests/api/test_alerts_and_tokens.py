import uuid

import pytest


@pytest.fixture
def auth_header(client):
    # Register and login a user to get a valid token
    email = f"user_{uuid.uuid4().hex[:6]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "name": "Test User"},
    )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    token = response.json()["token"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_alert(client, auth_header):
    payload = {
        "name": "US High Impact",
        "description": "Notify me for US high impact events",
        "conditions": [
            {"alert_type": "high_impact_event", "value": None},
            {"alert_type": "specific_country", "value": "United States"},
        ],
        "push_enabled": True,
    }
    response = client.post("/api/v1/alerts", json=payload, headers=auth_header)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "US High Impact"
    assert len(data["conditions"]) == 2
    return data["id"]


def test_list_alerts(client, auth_header):
    # Ensure there is at least one alert
    test_create_alert(client, auth_header)

    response = client.get("/api/v1/alerts", headers=auth_header)
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_update_alert(client, auth_header):
    alert_id = test_create_alert(client, auth_header)

    update_payload = {
        "name": "Updated Name",
        "push_enabled": False,
        "conditions": [{"alert_type": "high_impact_event", "value": None}],
    }
    response = client.put(f"/api/v1/alerts/{alert_id}", json=update_payload, headers=auth_header)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["push_enabled"] is False


def test_delete_alert(client, auth_header):
    alert_id = test_create_alert(client, auth_header)

    response = client.delete(f"/api/v1/alerts/{alert_id}", headers=auth_header)
    assert response.status_code == 204

    # Verify it's gone
    get_resp = client.get("/api/v1/alerts", headers=auth_header)
    ids = [a["id"] for a in get_resp.json()]
    assert alert_id not in ids


def test_register_device_token(client, auth_header):
    payload = {
        "token": "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]",
        "device_type": "ios",
        "device_name": "iPhone 15 Pro",
    }
    # Path is /api/v1/alerts/device-token based on alerts router being included under v1 prefix
    response = client.post("/api/v1/alerts/device-token", json=payload, headers=auth_header)
    assert response.status_code == 201
    assert response.json()["is_active"] is True
