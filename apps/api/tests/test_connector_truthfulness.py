import time

from fastapi.testclient import TestClient

from app.entrypoint import app


def session(client):
    suffix = str(time.time_ns())
    response = client.post('/auth/signup', json={
        'email': f'connector-{suffix}@example.com',
        'password': 'StrongPass123!',
        'name': 'Connector Test',
        'organization_name': f'Connector Org {suffix}',
        'preferred_language': 'en',
        'locale': 'en',
    })
    assert response.status_code == 200, response.text
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_connector_secret_is_never_returned_and_bad_token_is_not_connected():
    client = TestClient(app)
    headers = session(client)
    created = client.post('/integrations/connections', headers=headers, json={
        'provider': 'telegram',
        'display_name': 'Test Telegram',
        'config': {'bot_token': 'definitely-not-a-real-token', 'chat_id': '123'},
    })
    assert created.status_code == 200, created.text
    connection = created.json()
    assert connection['status'] == 'needs_setup'
    assert connection['config']['bot_token'] != 'definitely-not-a-real-token'
    assert 'definitely-not-a-real-token' not in created.text

    tested = client.post(f"/integrations/connections/{connection['id']}/test", headers=headers, json={})
    assert tested.status_code in (422, 502), tested.text
    fetched = client.get(f"/integrations/connections/{connection['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()['status'] == 'error'
    assert 'definitely-not-a-real-token' not in fetched.text
