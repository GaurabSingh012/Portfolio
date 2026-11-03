from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.request_middleware import install_request_middleware


def create_test_app():
    test_app = FastAPI()

    install_request_middleware(test_app)

    @test_app.post("/chat")
    def protected_chat():
        return {"message": "Authenticated successfully"}

    @test_app.get("/health")
    def health():
        return {"status": "healthy"}

    return test_app


def test_chat_rejects_missing_token(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("RAG_BACKEND_TOKEN", "test-secret")

    client = TestClient(create_test_app())

    response = client.post("/chat", json={})

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized."
    assert response.headers.get("X-Request-ID")


def test_chat_accepts_correct_token(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("RAG_BACKEND_TOKEN", "test-secret")

    client = TestClient(create_test_app())

    response = client.post(
        "/chat",
        json={},
        headers={"X-RAG-Backend-Token": "test-secret"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Authenticated successfully"


def test_health_remains_public(monkeypatch):
    monkeypatch.setenv("RAG_BACKEND_TOKEN", "test-secret")

    client = TestClient(create_test_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_production_fails_closed_without_token(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("RAG_BACKEND_TOKEN", raising=False)

    client = TestClient(create_test_app())

    response = client.post("/chat", json={})

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_invalid_request_id_is_replaced(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)

    client = TestClient(create_test_app())

    response = client.get(
        "/health",
        headers={"X-Request-ID": "invalid request id"},
    )

    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")

    assert request_id
    assert request_id != "invalid request id"