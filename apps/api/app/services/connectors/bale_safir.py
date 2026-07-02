import re, uuid
from .base import BaseConnector, CapabilityMatrix
ERROR_MAP={'InternalServerError':'Provider internal error','RateLimitExceeded':'Rate limit exceeded','InvalidInput':'Invalid request payload','InvalidPhone':'Invalid Iranian mobile number','NotBaleUser':'Recipient is not a Bale user','PaymentRequired':'Safir account requires payment','MaximumContactLimitReached':'Contact limit reached'}
def normalize_iran_phone(phone:str, plus=True):
    digits=re.sub(r'\D','',phone or '')
    if digits.startswith('0098'): digits=digits[2:]
    if digits.startswith('0') and len(digits)==11: digits='98'+digits[1:]
    if digits.startswith('912') and len(digits)==10: digits='98'+digits
    if not (digits.startswith('98') and len(digits)==12 and digits[2]=='9'): raise ValueError('InvalidPhone')
    return ('+' if plus else '')+digits
class BaleSafirConnector(BaseConnector):
    provider_name='bale_safir'; capabilities=CapabilityMatrix(direct_publish=False,assisted_publish=True,dm=True,approval_bot=True,requires_app_review=False,supports_webhook=True,supported_content_types=['text','document','image'])
    def send_message(self, phone_number, message_data, credentials=None, consent=False):
        if not consent: return {'sent':False,'error':'ConsentRequired'}
        phone=normalize_iran_phone(phone_number)
        return {'sent':True,'request_id':str(uuid.uuid4()),'message_id':'safir_'+uuid.uuid4().hex[:10],'phone_number':phone,'payload':{'bot_id':(credentials or {}).get('bot_id'),'message_data':message_data}}
    def map_error(self, code): return ERROR_MAP.get(code,'Unknown API error')
