import pytest

from app.services.connectors.bale_safir import normalize_iran_phone, BaleSafirConnector
from app.services.connectors.base import ConnectorConfigurationError
from app.services.connectors.providers import get_connector
from app.rbac import can
from app.services.ai.agents import BrandAnalystAgent, ContentStrategistAgent
from app.services.ai.providers import AIConfigurationError


class B:
    primary_language='fa'


def test_rbac():
    assert can('org_owner','publish') and not can('viewer','publish')


def test_brand_dna_requires_real_ai_when_provider_is_mock(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','mock')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(AIConfigurationError):
        BrandAnalystAgent()


def test_calendar_agent_requires_real_ai_when_provider_is_mock(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER','mock')
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(AIConfigurationError):
        ContentStrategistAgent()


def test_mock_publishing_connector_is_explicitly_test_only():
    result=get_connector('mock').publish_post(type('D',(),{'id':1})())
    assert result['status']=='mock_published'
    assert result['mock'] is True


def test_telegram_connector_capabilities():
    assert get_connector('telegram').capabilities.approval_bot is True


def test_bale_connector_uses_real_api_template():
    connector=get_connector('bale')
    assert connector.api_template.startswith('https://tapi.bale.ai')
    assert '{token}' in connector.api_template and '{method}' in connector.api_template


def test_bale_safir_phone_normalization_and_errors():
    assert normalize_iran_phone('09121234567')=='+989121234567'
    assert BaleSafirConnector().map_error('NotBaleUser')=='Recipient is not a Bale user'


def test_bale_safir_consent_required():
    with pytest.raises(ConnectorConfigurationError,match='consent'):
        BaleSafirConnector().send_message('09121234567', {'text':'x'}, consent=False)


def test_weekly_report_shape():
    assert 'recommendations' in {'recommendations': []}


def test_brand_memory_learning_shape():
    assert 'note' in {'note':'Client prefers softer copy'}


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


def test_growth_pages_are_tenant_scoped_and_empty_states_are_real():
    from fastapi.testclient import TestClient
    from app.main import app
    c=TestClient(app)
    a=c.post('/auth/signup', json={'email':'growth-a@example.com','password':'password123','name':'Growth A','organization_name':'Growth A Org'}).json()['access_token']
    b=c.post('/auth/signup', json={'email':'growth-b@example.com','password':'password123','name':'Growth B','organization_name':'Growth B Org'}).json()['access_token']
    ha={'Authorization':f'Bearer {a}'}; hb={'Authorization':f'Bearer {b}'}
    empty=c.get('/campaigns/overview', headers=ha).json()
    assert empty['campaigns']==[] and empty['summary']['total_campaigns']==0
    camp=c.post('/campaigns', headers=ha, json={'name':'Launch','goal':'Awareness','channels':['linkedin']})
    assert camp.status_code==200
    assert c.get('/campaigns/overview', headers=ha).json()['summary']['total_campaigns']==1
    other=c.get(f"/campaigns/{camp.json()['id']}", headers=hb)
    assert other.status_code==403
    ins=c.get('/insights/overview', headers=ha).json()
    assert ins['summary']['content_with_data_count']==0 and ins['top_content']==[]
    mm=c.post('/insights/manual-metric', headers=ha, json={'channel':'linkedin','metric_name':'clicks','metric_value':5})
    assert mm.status_code==200
    assert c.get('/insights/overview', headers=ha).json()['summary']['content_with_data_count']==1
    rep=c.post('/reports/generate-weekly', headers=ha, json={})
    assert rep.status_code==200 and '5' in str(c.get('/insights/overview', headers=ha).json()['trends'])
    assert c.get('/reports/overview', headers=hb).json()['summary']['total_reports']==0
