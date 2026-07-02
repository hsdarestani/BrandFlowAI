from .database import Base, engine, SessionLocal
from .models import *
from .security import hash_password
from .services.connectors.providers import get_connector
Base.metadata.create_all(bind=engine)
db=SessionLocal()
def user(email,name,super=False):
    u=db.query(User).filter_by(email=email).first() or User(email=email,name=name,password_hash=hash_password('password123'),is_super_admin=super,locale='en')
    db.add(u); db.flush(); return u
admin=user('admin@brandflow.ai','Super Admin',True); owner=user('owner@demo.com','Demo Owner'); approver=user('client@demo.com','Client Approver')
plan=Plan(name='MVP Pro',price_monthly=99,limits_json={'brands':10,'ai_credits':100000},features_json={'approval_links':True,'bale':True,'telegram':True}); db.add(plan); db.flush()
orgs=[('Aesthetic Clinic Germany','regulated'),('Iran Ecommerce Shop','ecommerce'),('German IT Services','owner'),('Agency Demo','agency')]
for name,mode in orgs:
    org=Organization(name=name,slug=name.lower().replace(' ','-'),mode=mode,plan_id=plan.id,owner_user_id=owner.id); db.add(org); db.flush(); db.add(OrganizationMember(organization_id=org.id,user_id=owner.id,role='org_owner')); db.add(OrganizationMember(organization_id=org.id,user_id=approver.id,role='client_approver'))
    lang='fa' if 'Iran' in name else 'de'; brand=Brand(organization_id=org.id,name=name+' Brand',slug=name.lower().replace(' ','-')+'-brand',industry='beauty' if 'Clinic' in name else 'ecommerce' if 'Iran' in name else 'it_services',country='IR' if lang=='fa' else 'DE',primary_language=lang,additional_languages=['en'],description='Seeded vertical slice demo brand',status='active'); db.add(brand); db.flush()
    db.add(BrandDNA(brand_id=brand.id,voice_json={'tone':'friendly','language':lang},visual_json={'colors':['#7c3aed','#06b6d4']},compliance_json={'regulated':mode=='regulated'},channel_rules_json={'bale':'price-first Persian CTA','telegram':'direct offer','instagram':'story-first'},cta_library_json={'items':['Book now','Order now','Mehr erfahren']},forbidden_words_json={'items':['guaranteed cure']}))
    for provider in (['telegram','bale','woocommerce','mock'] if lang=='fa' else ['instagram','linkedin','google_business','mock']): db.add(ChannelAccount(brand_id=brand.id,provider=provider,account_name=provider.title(),account_identifier='mock_'+provider,capabilities_json=get_connector(provider).capabilities.__dict__,credentials_encrypted_json={'mock':True}))
    db.add(ProductService(brand_id=brand.id,type='service' if mode=='regulated' else 'product',name='Signature Offer',description='Demo product/service',price=99,currency='IRR' if lang=='fa' else 'EUR'))
    for i in range(3): db.add(ContentPillar(brand_id=brand.id,name=['Education','Proof','Offer'][i],description='Seed pillar',weight=1))
    db.flush(); item=CalendarItem(brand_id=brand.id,title='Weekly AI content idea',description='Generated from seed data',channels_json=['telegram','bale'] if lang=='fa' else ['instagram','linkedin'],language=lang,content_type='post',status='draft_ready'); db.add(item); db.flush()
    draft=ContentDraft(calendar_item_id=item.id,brand_id=brand.id,channel=item.channels_json[0],content_type='post',language=lang,title='Demo draft',body='نمونه متن تایید محتوا' if lang=='fa' else 'Compliance-aware demo draft for approval.',hashtags_json=['#brandflowai'],created_by_user_id=owner.id); db.add(draft); db.flush(); ver=ContentVersion(draft_id=draft.id,version_number=1,title=draft.title,body=draft.body,created_by_user_id=owner.id); db.add(ver); db.flush(); draft.current_version_id=ver.id
    db.add(ApprovalRequest(draft_id=draft.id,requested_by_user_id=owner.id,assigned_to_user_id=approver.id,public_token_hash='demo-token-hash',status='pending'))
    pp=PublishedPost(draft_id=draft.id,channel_account_id=db.query(ChannelAccount).filter_by(brand_id=brand.id).first().id,provider_post_id='mock_post',public_url='https://mock.social/demo'); db.add(pp); db.flush(); db.add(InsightSnapshot(published_post_id=pp.id,metrics_json={'impressions':1200,'orders':3,'revenue':450},normalized_scores_json={'awareness_score':84,'conversion_score':67})); db.add(WeeklyReport(brand_id=brand.id,week_start='2026-06-29',week_end='2026-07-05',summary='Seeded weekly report with recommendations.',insights_json={'best_channel':item.channels_json[0]},recommendations_json={'next':['Generate smarter next calendar']})); db.add(BrandMemoryNote(brand_id=brand.id,note='Client prefers softer sales copy on Instagram and direct price CTA on Telegram/Bale.',source_type='seed',confidence_score=.9))
for key in ['ai_generation','direct_publishing','analytics','approval_links','telegram_bot','bale_bot','bale_safir','ecommerce','regulated_mode','agency_mode','local_iranian_connectors']: db.add(FeatureFlag(key=key,enabled=True))
for jt in ['content_generation','calendar_generation','publishing','analytics_fetch','report_generation','bale_send','bale_safir_send']: db.add(JobLog(job_type=jt,status='completed',result_json={'seed':True}))
db.commit(); print('Seeded BrandFlow AI demo data. Demo password: password123')
