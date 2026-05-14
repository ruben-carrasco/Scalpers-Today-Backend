import uuid

from scalper_today.api.dependencies import Container


def _register_and_get_token(client) -> str:
    email = f"assistant_{uuid.uuid4().hex[:8]}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strongPassword123", "name": "Assistant User"},
    )
    assert response.status_code == 201
    return response.json()["token"]["access_token"]


def test_assistant_chat_requires_auth(client):
    response = client.post(
        "/api/v1/assistant/chat",
        json={"question": "Qué es el IPC?"},
    )

    assert response.status_code in (401, 403)


def test_assistant_chat_returns_answer(client, monkeypatch):
    token = _register_and_get_token(client)

    async def fake_generate_assistant_response(question, context=None):
        assert question == "Qué es el IPC?"
        assert context["screen"] == "home"
        return "El IPC mide la evolución de precios de una cesta de consumo."

    monkeypatch.setattr(
        Container.get_instance().analyzer,
        "generate_assistant_response",
        fake_generate_assistant_response,
    )

    response = client.post(
        "/api/v1/assistant/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Qué es el IPC?", "context": {"screen": "home"}},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"].startswith("El IPC mide")
    assert "asesoramiento financiero" in data["disclaimer"]
