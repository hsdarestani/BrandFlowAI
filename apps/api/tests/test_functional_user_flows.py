import base64
import json
import time

from fastapi.testclient import TestClient

from app.entrypoint import app


def _session(client: TestClient):
    suffix = f"{time.time_ns()}"
    response = client.post(
        "/auth/signup",
        json={
            "email": f"functional-{suffix}@example.com",
            "password": "StrongPass123!",
            "name": "Functional Test",
            "organization_name": f"Functional Org {suffix}",
            "preferred_language": "en",
            "locale": "en",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_export_billing_and_integrations_are_truthful(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    headers = _session(client)

    billing = client.get("/settings/billing", headers=headers)
    assert billing.status_code == 200, billing.text
    assert billing.json()["billing_provider_connected"] is False

    catalog = client.get("/integrations/catalog", headers=headers)
    assert catalog.status_code == 200, catalog.text
    rows = catalog.json()
    assert rows
    assert all(row["provider"] != "mock" for row in rows)
    instagram = next(row for row in rows if row["provider"] == "instagram")
    assert instagram["is_assisted"] is True
    assert instagram["capabilities"]["can_publish"] is False

    exported = client.post("/settings/export-data", headers=headers)
    assert exported.status_code == 200, exported.text
    payload = exported.json()
    assert payload["available"] is True
    data = json.loads(payload["content"])
    assert data["user"]["email"].startswith("functional-")
    assert data["brand_pulse"] is not None


def test_report_pdf_is_a_real_pdf_without_fake_performance(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    headers = _session(client)

    generated = client.post("/reports/generate-weekly", headers=headers, json={})
    assert generated.status_code == 200, generated.text
    report = generated.json()
    assert "No performance metrics were available" in report["summary"] or report["metrics"] == {}

    exported = client.post(f"/reports/{report['id']}/export", headers=headers, json={"format": "pdf"})
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert body["available"] is True
    raw = base64.b64decode(body["content_base64"])
    assert raw.startswith(b"%PDF")
    assert len(raw) > 500


def test_live_ai_test_refuses_to_fake_success_without_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "mock")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    headers = _session(client)
    response = client.post("/settings/ai-provider/test", headers=headers, json={})
    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "missing_credentials"
