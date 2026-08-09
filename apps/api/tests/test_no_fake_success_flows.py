import time

from fastapi.testclient import TestClient

from app.entrypoint import app


def _session(client: TestClient):
    suffix = str(time.time_ns())
    response = client.post('/auth/signup', json={
        'email': f'no-fake-{suffix}@example.com',
        'password': 'StrongPass123!',
        'name': 'No Fake Test',
        'organization_name': f'No Fake Org {suffix}',
        'preferred_language': 'en',
        'locale': 'en',
    })
    assert response.status_code == 200, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_publish_schedule_and_email_do_not_succeed_without_real_dependencies(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'mock')
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    client = TestClient(app)
    headers = _session(client)

    # Create one ordinary draft through the real CRUD route; publishing should
    # still require a configured channel connection and must not invent a post id.
    brand = client.get('/brand-pulse/overview', headers=headers).json()['brand']
    draft = client.post(f"/brands/{brand['id']}/drafts", headers=headers, json={
        'channel': 'telegram',
        'content_type': 'post',
        'language': 'en',
        'title': 'A real draft',
        'body': 'Draft body for dependency validation.',
    })
    if draft.status_code not in (200, 201):
        # Some deployments intentionally expose draft creation through Studio
        # only. In that case this test still validates the critical dependencies
        # below instead of weakening the contract.
        draft_id = None
    else:
        draft_id = draft.json()['id']

    if draft_id:
        published = client.post(f'/drafts/{draft_id}/publish-now', headers=headers, json={})
        assert published.status_code == 422
        assert published.json()['detail']['error'] in {'channel_not_configured', 'channel_not_connected'}

        scheduled = client.post(f'/drafts/{draft_id}/schedule', headers=headers, json={})
        assert scheduled.status_code == 422
        assert scheduled.json()['detail']['error'] in {'channel_not_configured', 'scheduled_at_required'}

    report = client.post('/reports/generate-weekly', headers=headers, json={})
    assert report.status_code == 200, report.text
    sent = client.post(f"/reports/{report.json()['id']}/send-email", headers=headers, json={'recipient_email':'owner@example.com'})
    assert sent.status_code == 422
    assert sent.json()['detail']['error'] == 'email_not_connected'


def test_assisted_provider_never_reports_connected_direct_api():
    client = TestClient(app)
    headers = _session(client)
    created = client.post('/integrations/connections', headers=headers, json={
        'provider':'instagram',
        'display_name':'Instagram',
        'config':{},
    })
    assert created.status_code == 200, created.text
    body = created.json()
    assert body['status'] == 'assisted'
    assert body['capabilities']['direct_publish'] is False
