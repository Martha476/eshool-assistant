from fastapi.testclient import TestClient

from app import main, service
from app.schemas import AssistantResponse

client = TestClient(main.app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_home_serves_search_assistant_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "Describe the school" in response.text
    assert '/static/app.js' in response.text


def test_static_frontend_assets_are_served():
    assert client.get("/static/styles.css").status_code == 200
    script = client.get("/static/app.js")
    assert script.status_code == 200 and 'fetch("/search"' in script.text


def test_search_endpoint_returns_assistant_response(monkeypatch):
    monkeypatch.setattr(
        main, "handle", lambda text: AssistantResponse(status="needs_clarification", message="Where?")
    )
    r = client.post("/search", json={"request": "a school"})
    assert r.status_code == 200 and r.json()["status"] == "needs_clarification"


def test_missing_request_field_is_422():
    assert client.post("/search", json={}).status_code == 422


def test_empty_request_handled_by_service():
    r = client.post("/search", json={"request": "  "})
    assert r.status_code == 200 and r.json()["status"] == "error"