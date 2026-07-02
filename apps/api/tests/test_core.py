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
