from dataclasses import dataclass, field
@dataclass
class CapabilityMatrix:
    direct_publish: bool=False; assisted_publish: bool=True; analytics: bool=False; comments: bool=False; dm: bool=False; approval_bot: bool=False; media_upload: bool=False; schedule: bool=False; requires_app_review: bool=True; supports_webhook: bool=False; supports_polling: bool=False; supported_content_types: list[str]=field(default_factory=lambda:['text'])
class BaseConnector:
    provider_name='base'; capabilities=CapabilityMatrix()
    def connect_url(self): return None
    def oauth_callback(self,payload): return {'connected': True}
    def refresh_token(self,credentials): return credentials
    def validate_credentials(self,credentials): return {'valid': True, 'mode': 'mock'}
    def publish_post(self,draft, account=None): return {'status':'needs_manual_action','assisted_publish_url':f'/assisted/{getattr(draft,"id","draft")}' }
    def schedule_post(self,draft, when, account=None): return {'status':'scheduled','scheduled_at':str(when)}
    def get_post_status(self,provider_post_id): return {'status':'published'}
    def fetch_analytics(self,provider_post_id): return {'impressions':1000,'reach':700,'likes':50,'clicks':10}
    def fetch_comments(self,provider_post_id): return []
    def send_message(self,*a,**k): return {'sent': True}
    def revoke_connection(self,*a,**k): return {'revoked': True}
class MockConnector(BaseConnector):
    provider_name='mock'; capabilities=CapabilityMatrix(direct_publish=True,assisted_publish=True,analytics=True,comments=True,dm=True,approval_bot=True,media_upload=True,schedule=True,requires_app_review=False,supports_webhook=True,supports_polling=True,supported_content_types=['text','image','video','carousel','document'])
    def publish_post(self,draft, account=None): return {'status':'published','provider_post_id':f'mock_{getattr(draft,"id",1)}','public_url':f'https://mock.social/posts/{getattr(draft,"id",1)}'}
