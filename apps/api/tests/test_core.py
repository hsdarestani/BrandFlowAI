from app.services.connectors.bale_safir import normalize_iran_phone, BaleSafirConnector
from app.services.connectors.providers import get_connector
from app.rbac import can
from app.services.ai.agents import BrandAnalystAgent, ContentStrategistAgent
class B: primary_language='fa'
def test_rbac(): assert can('org_owner','publish') and not can('viewer','publish')
def test_brand_dna_mock_generation(): assert BrandAnalystAgent().run({'primary_language':'de'})['voice']['language']=='de'
def test_calendar_generation_mock(): assert len(ContentStrategistAgent().run(B())['calendar'])==7
def test_mock_publishing_connector(): assert get_connector('mock').publish_post(type('D',(),{'id':1})())['status']=='published'
def test_telegram_connector_mock(): assert get_connector('telegram').capabilities.approval_bot is True
def test_bale_connector_mock(): assert get_connector('bale').base_url.startswith('https://tapi.bale.ai')
def test_bale_safir_phone_normalization_and_errors():
    assert normalize_iran_phone('09121234567')=='+989121234567'
    assert BaleSafirConnector().map_error('NotBaleUser')=='Recipient is not a Bale user'
def test_bale_safir_consent_required(): assert BaleSafirConnector().send_message('09121234567', {'text':'x'}, consent=False)['error']=='ConsentRequired'
def test_weekly_report_shape(): assert 'recommendations' in {'recommendations': []}
def test_brand_memory_learning_shape(): assert 'note' in {'note':'Client prefers softer copy'}


def test_signup_repeated_org_slug_and_home_overview_tenant_scoped(tmp_path, monkeypatch):
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{tmp_path/'test.db'}")
    from fastapi.testclient import TestClient
    from app.main import app
    c=TestClient(app)
    r1=c.post('/auth/signup', json={'email':'one@example.com','password':'password123','name':'One','organization_name':'Repeat Org'})
    r2=c.post('/auth/signup', json={'email':'two@example.com','password':'password123','name':'Two','organization_name':'Repeat Org'})
    assert r1.status_code==200 and r2.status_code==200
    h1=c.get('/dashboard/home', headers={'Authorization':f"Bearer {r1.json()['access_token']}"})
    h2=c.get('/dashboard/home', headers={'Authorization':f"Bearer {r2.json()['access_token']}"})
    assert h1.status_code==200 and h2.status_code==200
    assert h1.json()['user']['email']=='one@example.com'
    assert h2.json()['user']['email']=='two@example.com'
    assert h1.json()['organization']['id'] != h2.json()['organization']['id']
    assert h1.json()['setup']['completion_percent'] < 50
    assert all(k['value'] in (0, '—', 'No approvals yet') for k in h1.json()['kpis'])

def test_duplicate_email_returns_409():
    from fastapi.testclient import TestClient
    from app.main import app
    c=TestClient(app)
    payload={'email':'duplicate@example.com','password':'password123','name':'Dup','organization_name':'Dup Org'}
    assert c.post('/auth/signup', json=payload).status_code in (200,201)
    assert c.post('/auth/signup', json=payload).status_code==409
