from .base import BaseConnector, MockConnector, CapabilityMatrix
from .bale_safir import BaleSafirConnector
class TelegramConnector(BaseConnector):
    provider_name='telegram'; capabilities=CapabilityMatrix(direct_publish=True,assisted_publish=True,approval_bot=True,media_upload=True,schedule=True,requires_app_review=False,supports_webhook=True,supports_polling=True,supported_content_types=['text','photo','video','document','media_group'])
    def send_message(self,chat_id,text,**kw): return {'ok':True,'result':{'message_id':1,'chat_id':chat_id,'text':text}}
class BaleConnector(TelegramConnector):
    provider_name='bale'; capabilities=CapabilityMatrix(direct_publish=True,assisted_publish=True,analytics=False,comments=False,dm=True,approval_bot=True,media_upload=True,schedule=True,requires_app_review=False,supports_webhook=True,supports_polling=True,supported_content_types=['text','photo','video','document','media_group'])
    base_url='https://tapi.bale.ai/bot{token}/{method}'
    def map_error(self, status, payload=None):
        desc=(payload or {}).get('description','').lower()
        if status==401 or 'token' in desc: return 'invalid token'
        if 'chat' in desc: return 'invalid chat id'
        if status==403: return 'forbidden'
        if status==429: return 'rate limit'
        if status==400: return 'bad request'
        return 'unknown API error'
class SkeletonConnector(BaseConnector):
    def __init__(self,name,app_review=True): self.provider_name=name; self.capabilities=CapabilityMatrix(assisted_publish=True,requires_app_review=app_review,supported_content_types=['text','image','video'])
CONNECTORS={c.provider_name:c for c in [MockConnector(),TelegramConnector(),BaleConnector(),BaleSafirConnector()]}
for n in ['instagram','facebook','tiktok','linkedin','google_business','youtube','woocommerce','ga4','brevo','mailchimp','booking','eitaa','soroush','aparat']:
    CONNECTORS[n]=SkeletonConnector(n, app_review=n not in ['woocommerce','ga4'])
def get_connector(provider): return CONNECTORS.get(provider, CONNECTORS['mock'])
def connector_catalog(): return [{'provider':k,'capabilities':v.capabilities.__dict__} for k,v in CONNECTORS.items()]
