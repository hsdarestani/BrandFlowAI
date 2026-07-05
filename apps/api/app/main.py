from fastapi import FastAPI, Depends, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from secrets import token_urlsafe
from hashlib import sha256
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from .database import Base, engine, get_db
from . import models as m
from .security import hash_password, verify_password, create_token, decode_token
from .services.ai.agents import BrandAnalystAgent, ContentStrategistAgent, CopywriterAgent, ApprovalLearningAgent, PerformanceAnalystAgent
from .services.connectors.providers import get_connector, connector_catalog
from .services.connectors.bale_safir import normalize_iran_phone
import os, re
Base.metadata.create_all(bind=engine)
app=FastAPI(title='Smarbiz API', version='0.1.0')
cors_origins=[o.strip() for o in os.getenv('CORS_ORIGINS','http://localhost:3000,https://smarbiz.sbs,https://www.smarbiz.sbs').split(',') if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
class Signup(BaseModel): email:str; password:str; name:str='Smarbiz User'; locale:str='en'; organization_name:str='Smarbiz Workspace'; preferred_language:str|None=None
class Login(BaseModel): email:str; password:str
class OrgIn(BaseModel): name:str; mode:str='owner'
class BrandIn(BaseModel): organization_id:int; name:str; industry:str='general'; country:str='DE'; primary_language:str='en'; timezone:str='UTC'; description:str=''
class ActionIn(BaseModel): action:str; comment:str|None=None; revision_prompt:str|None=None; save_to_memory:bool=True
class DraftPatch(BaseModel): title:str|None=None; body:str|None=None; status:str|None=None
class CalendarItemIn(BaseModel):
    brand_id:int|None=None; campaign_id:int|None=None; title:str=Field(min_length=1); description:str=''
    channel:str='instagram'; content_type:str='post'; status:str='idea'; scheduled_at:datetime|None=None; timezone:str|None=None; owner_user_id:int|None=None
class CalendarGenerateIn(BaseModel): brand_id:int|None=None; week_start:datetime|None=None; channels:list[str]|None=None; campaign_id:int|None=None

def slugify(value:str):
    slug=re.sub(r'[^a-z0-9]+','-',value.lower()).strip('-')
    return slug or 'workspace'
def make_unique_org_slug(db:Session, org_name:str):
    base=slugify(org_name); slug=base; i=2
    while db.query(m.Organization).filter_by(slug=slug).first(): slug=f'{base}-{i}'; i+=1
    return slug
def user_org_ids(db:Session,u):
    return [x.organization_id for x in db.query(m.OrganizationMember).filter_by(user_id=u.id,status='active').all()] or [x.id for x in db.query(m.Organization).filter_by(owner_user_id=u.id).all()]
def user_brands(db:Session,u):
    ids=user_org_ids(db,u)
    return db.query(m.Brand).filter(m.Brand.organization_id.in_(ids)).all() if ids else []
def require_brand(db:Session,u,brand_id:int|None=None):
    brands=user_brands(db,u)
    if not brands: return None
    b=next((x for x in brands if x.id==brand_id),None) if brand_id else brands[0]
    if brand_id and not b: raise HTTPException(403,'Brand is outside your workspace')
    return b
def parse_dt(value):
    if not value: return None
    if isinstance(value, datetime): return value
    return datetime.fromisoformat(str(value).replace('Z','+00:00'))
def item_channel(item): return (item.channels_json or ['other'])[0]
def calendar_item_out(item, db:Session):
    owner=db.get(m.User,item.assigned_user_id or item.created_by_user_id) if (item.assigned_user_id or item.created_by_user_id) else None
    return {'id':item.id,'title':item.title,'description':item.description,'channel':item_channel(item),'content_type':item.content_type,'status':normalize_status(item.status),'scheduled_at':item.scheduled_at.isoformat() if item.scheduled_at else None,'owner':({'id':owner.id,'name':owner.name} if owner else None),'campaign':None,'quality_score':None,'warning_count':1 if float(item.risk_score or 0)>.5 else 0,'href':f'/app/calendar?item={item.id}'}
def normalize_status(status):
    return {'planned':'idea','draft_ready':'draft','approval':'in_review'}.get(status,status or 'idea')
def setup_state(db:Session,b):
    if not b: return {'can_generate_week':False,'missing_requirements':[]}
    missing=[]
    if not db.query(m.BrandDNA).filter_by(brand_id=b.id).first(): missing.append({'id':'brand_pulse','title':'Brand Pulse not completed','action_href':'/app/brand-dna'})
    if db.query(m.ProductService).filter_by(brand_id=b.id).count()==0: missing.append({'id':'product_service','title':'No product/service added','action_href':'/app/settings'})
    if db.query(m.ChannelAccount).filter_by(brand_id=b.id).count()==0: missing.append({'id':'channels','title':'No channels selected','action_href':'/app/integrations'})
    if not any(a.connection_status in ('connected','mock_connected','mock') for a in db.query(m.ChannelAccount).filter_by(brand_id=b.id).all()): missing.append({'id':'approval','title':'No approval method connected','action_href':'/app/integrations'})
    return {'can_generate_week':not missing,'missing_requirements':missing}


def slugify(value:str):
    slug=re.sub(r'[^a-z0-9]+','-',(value or 'workspace').strip().lower()).strip('-')
    return slug or 'workspace'

def make_unique_org_slug(db:Session, org_name:str):
    base=slugify(org_name); slug=base; i=2
    while db.query(m.Organization).filter_by(slug=slug).first():
        slug=f'{base}-{i}'; i+=1
    return slug

def current_org(db:Session,u):
    mem=db.query(m.OrganizationMember).filter_by(user_id=u.id,status='active').first()
    if mem: return db.get(m.Organization,mem.organization_id)
    return db.query(m.Organization).filter_by(owner_user_id=u.id).first()

def active_brand(db:Session,org):
    if not org: return None
    return db.query(m.Brand).filter_by(organization_id=org.id).order_by(m.Brand.created_at.asc()).first()

def setup_status(done, possible):
    return 'done' if done else ('in_progress' if possible else 'not_started')

def build_home_overview(db:Session,u):
    org=current_org(db,u); brand=active_brand(db,org)
    now=datetime.now(timezone.utc); week_ago=now-timedelta(days=6)
    dna=db.query(m.BrandDNA).filter_by(brand_id=brand.id).first() if brand else None
    products=db.query(m.ProductService).filter_by(brand_id=brand.id).count() if brand else 0
    channels=db.query(m.ChannelAccount).filter(m.ChannelAccount.brand_id==brand.id,m.ChannelAccount.connection_status.in_(['connected','mock_connected','mock'])).count() if brand else 0
    approval_methods=channels
    calendar_count=db.query(m.CalendarItem).filter_by(brand_id=brand.id).count() if brand else 0
    draft_count=db.query(m.ContentDraft).filter_by(brand_id=brand.id).count() if brand else 0
    approvals_q=db.query(m.ApprovalRequest).join(m.ContentDraft,m.ContentDraft.id==m.ApprovalRequest.draft_id).filter(m.ContentDraft.brand_id==brand.id) if brand else None
    approval_count=approvals_q.count() if approvals_q else 0
    pending_approvals=approvals_q.filter(m.ApprovalRequest.status=='pending').count() if approvals_q else 0
    published=db.query(m.PublishedPost).join(m.ContentDraft,m.ContentDraft.id==m.PublishedPost.draft_id).filter(m.ContentDraft.brand_id==brand.id).count() if brand else 0
    reports=db.query(m.WeeklyReport).filter_by(brand_id=brand.id).count() if brand else 0
    step_defs=[
      ('create_brand','Create brand','Create your first brand workspace.',bool(brand),True,5,'Create brand','/onboarding'),
      ('brand_pulse','Complete Brand Pulse / Brand DNA','Teach Smarbiz your voice, offers, and rules.',bool(dna),bool(brand),15,'Complete Brand Pulse','/app/brand-dna'),
      ('product_service','Add product/service','Add at least one offer to promote.',products>0,bool(dna),8,'Add product/service','/app/brand-dna?section=offers'),
      ('content_channels','Choose content channels','Select the channels you want to publish to.',channels>0,products>0,5,'Choose channels','/app/integrations'),
      ('approval_method','Connect at least one approval method','Connect an approval path for reviews.',approval_methods>0,channels>0,5,'Connect approval channel','/app/integrations?type=approval'),
      ('generate_week','Generate first week','Create your first weekly content plan.',calendar_count>0,approval_methods>0,10,'Generate first week','/app/calendar?generate=1'),
      ('create_draft','Create first draft','Generate or write your first draft.',draft_count>0,calendar_count>0,10,'Create first draft','/app/content-studio?new=1'),
      ('send_approval','Send first approval','Send a draft to approval.',approval_count>0,draft_count>0,3,'Send for approval','/app/content-studio?status=draft'),
      ('publish_post','Publish first post','Publish or schedule approved content.',published>0,approval_count>0,5,'Publish post','/app/calendar?status=scheduled'),
      ('review_insight','Review first insight','Review performance after publishing.',reports>0 or published>0,published>0,5,'Review insights','/app/reports')
    ]
    steps=[{'id':i,'title':t,'description':d,'status':setup_status(done,poss),'estimated_time_minutes':mins,'action_label':al,'action_href':href} for i,t,d,done,poss,mins,al,href in step_defs]
    done=sum(1 for x in steps if x['status']=='done'); first=next((x['id'] for x in steps if x['status']!='done'),None)
    drafts_waiting=db.query(m.ContentDraft).filter(m.ContentDraft.brand_id==brand.id,m.ContentDraft.status.in_(['draft','draft_ready','in_review'])).count() if brand else 0
    scheduled=db.query(m.ScheduledPost).join(m.ContentDraft,m.ContentDraft.id==m.ScheduledPost.draft_id).filter(m.ContentDraft.brand_id==brand.id,m.ScheduledPost.status=='scheduled',m.ScheduledPost.scheduled_at>=now).count() if brand else 0
    approved=approvals_q.filter(m.ApprovalRequest.status=='approved').count() if approvals_q else 0
    approval_rate='No approvals yet' if approval_count==0 else f'{round(approved/approval_count*100)}%'
    usage=db.query(m.AIUsageLog).filter(m.AIUsageLog.organization_id==org.id).count() if org else 0
    kpis=[{'id':'drafts_waiting','label':'Drafts waiting','value':drafts_waiting,'href':'/app/content-studio?status=draft','helper':'Drafts or reviews needing attention'}, {'id':'posts_scheduled','label':'Posts scheduled','value':scheduled,'href':'/app/calendar?status=scheduled','helper':'Upcoming scheduled posts'}, {'id':'channels_connected','label':'Channels connected','value':channels,'href':'/app/integrations','helper':'Connected publishing or approval channels'}, {'id':'ai_credits','label':'AI credits','value':'—','href':'/app/settings?section=usage','helper':'Not tracked yet' if usage==0 else f'{usage} AI operations logged'}, {'id':'quality_warnings','label':'Quality warnings','value':0,'href':'/app/content-studio?filter=warnings','helper':'No warnings yet'}, {'id':'approval_rate','label':'Approval rate','value':approval_rate,'href':'/app/reports?section=approvals','helper':'Approved requests divided by total requests'}]
    days=[]
    for n in range(7):
      day=(week_ago+timedelta(days=n)).date(); start=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc); end=start+timedelta(days=1)
      gen=db.query(m.ContentDraft).filter(m.ContentDraft.brand_id==brand.id,m.ContentDraft.created_at>=start,m.ContentDraft.created_at<end).count() if brand else 0
      appr=approvals_q.filter(m.ApprovalRequest.updated_at>=start,m.ApprovalRequest.updated_at<end,m.ApprovalRequest.status=='approved').count() if approvals_q else 0
      pub=db.query(m.PublishedPost).join(m.ContentDraft,m.ContentDraft.id==m.PublishedPost.draft_id).filter(m.ContentDraft.brand_id==brand.id,m.PublishedPost.published_at>=start,m.PublishedPost.published_at<end).count() if brand else 0
      days.append({'day':day.isoformat(),'generated':gen,'approved':appr,'published':pub})
    pipeline=[]
    for status,label,href in [('ideas','Ideas','/app/content-studio?status=ideas'),('drafts','Drafts','/app/content-studio?status=draft'),('in_review','In review','/app/content-studio?status=in_review'),('approved','Approved','/app/content-studio?status=approved'),('scheduled','Scheduled','/app/calendar?status=scheduled'),('published','Published','/app/calendar?status=published')]:
      q=db.query(m.ContentDraft).filter_by(brand_id=brand.id) if brand else None
      items=[]; count=0
      if q and status in ['drafts','in_review','approved']:
        statuses={'drafts':['draft','draft_ready'],'in_review':['in_review'],'approved':['approved']}[status]; rows=q.filter(m.ContentDraft.status.in_(statuses)).order_by(m.ContentDraft.updated_at.desc()).all(); count=len(rows); items=[{'id':r.id,'title':r.title,'channel':r.channel,'href':f'/app/content-studio?draft={r.id}'} for r in rows[:3]]
      elif brand and status=='scheduled': count=scheduled
      elif brand and status=='published': count=published
      elif brand and status=='ideas': count=db.query(m.CalendarItem).filter_by(brand_id=brand.id,status='planned').count()
      pipeline.append({'status':status,'label':label,'count':count,'href':href,'items':items})
    recent=[]
    if brand:
      for r in db.query(m.ContentDraft).filter_by(brand_id=brand.id).order_by(m.ContentDraft.updated_at.desc()).limit(6): recent.append({'id':r.id,'title':r.title,'type':'Draft','status':r.status,'channel':r.channel,'score':float(r.brand_fit_score) if r.brand_fit_score is not None else None,'updated_at':r.updated_at.isoformat() if hasattr(r.updated_at,'isoformat') else str(r.updated_at),'href':f'/app/content-studio?draft={r.id}'})
    alerts=[]
    if channels==0: alerts.append({'id':'no_channels','title':'No connected channels','description':'Connect a publishing or approval channel.','severity':'warning','href':'/app/integrations'})
    if approval_methods==0: alerts.append({'id':'missing_approval','title':'Missing approval channel','description':'Connect at least one approval method.','severity':'warning','href':'/app/integrations?type=approval'})
    if calendar_count==0: alerts.append({'id':'no_content','title':'No content generated','description':'Generate your first week to start tracking activity.','severity':'info','href':'/app/calendar?generate=1'})
    if pending_approvals: alerts.append({'id':'pending_approvals','title':'Pending approvals','description':f'{pending_approvals} approval request(s) need review.','severity':'warning','href':'/app/approvals?status=pending'})
    rec=next((x for x in steps if x['status']!='done'),None)
    action={'title':rec['title'] if rec else 'Review insights','description':rec['description'] if rec else 'Your setup is complete. Review reports and plan the next cycle.','action_label':rec['action_label'] if rec else 'Open reports','action_href':rec['action_href'] if rec else '/app/reports','severity':'warning' if rec else 'success','missing_requirements':[x['title'] for x in steps if x['status']!='done'][:2] if rec and rec['status']=='not_started' else []}
    return {'user':{'id':u.id,'name':u.name,'email':u.email},'organization':({'id':org.id,'name':org.name,'mode':org.mode} if org else None),'brand':({'id':brand.id,'name':brand.name,'industry':brand.industry,'primary_language':brand.primary_language,'setup_status':brand.status} if brand else None),'setup':{'completion_percent':round(done/len(steps)*100),'first_incomplete_step_id':first,'steps':steps},'kpis':kpis,'weekly_activity':days,'pipeline':pipeline,'recent_work':recent,'recommended_action':action,'alerts':alerts,'memory_summary':{'title':'Smarbiz Memory','description':('Brand DNA captured' if dna else 'Brand memory is not configured yet'),'href':'/app/brand-dna'},'channel_health':{'title':'Channel Health','description':f'{channels} connected channel(s)' if channels else 'No channels connected','status':'good' if channels else 'missing','href':'/app/integrations'},'approval_status_summary':{'pending':pending_approvals,'approved':approved,'total':approval_count}}


def make_unique_org_slug(db, org_name:str):
    base='-'.join((org_name or 'smarbiz-workspace').lower().split()) or 'smarbiz-workspace'
    slug=base; i=2
    while db.query(m.Organization).filter_by(slug=slug).first():
        slug=f'{base}-{i}'; i+=1
    return slug

def user_from_auth(authorization:str|None=Header(default=None), db:Session=Depends(get_db)):
    if not authorization: raise HTTPException(401,'Missing bearer token')
    try: email=decode_token(authorization.replace('Bearer ',''))['sub']
    except Exception: raise HTTPException(401,'Invalid token')
    u=db.query(m.User).filter_by(email=email).first()
    if not u: raise HTTPException(401,'Unknown user')
    return u
@app.get('/health')
def health(): return {'ok':True,'service':'smarbiz'}
@app.post('/auth/signup')
def signup(data:Signup, db:Session=Depends(get_db)):
    email=data.email.strip().lower()
    if len(data.password)<8: raise HTTPException(422,'Password must be at least 8 characters')
    if db.query(m.User).filter_by(email=email).first(): raise HTTPException(409,'Email exists')
    locale=(data.preferred_language or data.locale or 'en')
    u=m.User(email=email,password_hash=hash_password(data.password),name=data.name.strip() or 'Smarbiz User',locale=locale,is_super_admin=email.startswith('admin@'))
    db.add(u); db.flush()
    org_name=(data.organization_name or f"{u.name}'s workspace").strip()
    org=m.Organization(name=org_name,slug=make_unique_org_slug(db, org_name),mode='owner',owner_user_id=u.id)
    db.add(org); db.flush()
    db.add(m.OrganizationMember(organization_id=org.id,user_id=u.id,role='org_owner'))
    brand=m.Brand(organization_id=org.id,name=org_name,slug=org.slug+'-brand',industry='general',country='DE',primary_language=locale,timezone='UTC',description='Created during Smarbiz signup',status='onboarding')
    db.add(brand); db.flush()
    for key,label in [('brand','Create brand'),('voice','Set voice'),('channels','Choose channels'),('approval','Approval path'),('first_week','First week')]:
        db.add(m.SetupChecklistItem(brand_id=brand.id,key=key,label=label,status='pending'))
    db.commit()
    return {'access_token':create_token(u.email),'user':{'id':u.id,'email':u.email,'name':u.name,'is_super_admin':u.is_super_admin},'organization':{'id':org.id,'name':org.name},'brand':{'id':brand.id,'name':brand.name}}
@app.get('/dashboard/home')
def dashboard_home(u=Depends(user_from_auth),db:Session=Depends(get_db)):
    return build_home_overview(db,u)
@app.get('/environment')
def environment(): return {'mode':'Demo mode' if DEMO_MODE else 'Production mode'}

@app.post('/auth/login')
def login(data:Login, db:Session=Depends(get_db)):
    u=db.query(m.User).filter_by(email=data.email).first()
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Bad credentials')
    return {'access_token':create_token(u.email),'user':{'id':u.id,'email':u.email,'is_super_admin':u.is_super_admin}}
@app.post('/auth/logout')
def logout(): return {'ok':True}
@app.get('/auth/me')
def me(u=Depends(user_from_auth)): return {'id':u.id,'email':u.email,'name':u.name,'locale':u.locale,'is_super_admin':u.is_super_admin}
@app.post('/auth/invitations/accept')
def accept_invitation(): return {'status':'accepted_placeholder'}
@app.get('/organizations')
def organizations(u=Depends(user_from_auth), db:Session=Depends(get_db)):
    ids=user_org_ids(db,u); return db.query(m.Organization).filter(m.Organization.id.in_(ids)).all() if ids else []
@app.post('/organizations')
def create_org(data:OrgIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    org=m.Organization(name=data.name,slug=data.name.lower().replace(' ','-'),mode=data.mode,owner_user_id=u.id); db.add(org); db.flush(); db.add(m.OrganizationMember(organization_id=org.id,user_id=u.id,role='org_owner')); db.commit(); return org
@app.get('/organizations/{id}')
def get_org(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.get(m.Organization,id)
@app.patch('/organizations/{id}')
def patch_org(id:int,data:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): org=db.get(m.Organization,id); [setattr(org,k,v) for k,v in data.items() if hasattr(org,k)]; db.commit(); return org
@app.get('/organizations/{id}/members')
def org_members(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.OrganizationMember).filter_by(organization_id=id).all()
@app.post('/organizations/{id}/invite')
def invite(id:int,payload:dict,u=Depends(user_from_auth)): return {'status':'invited','email':payload.get('email'),'role':payload.get('role','viewer')}
@app.patch('/organizations/{id}/members/{member_id}')
def member_patch(id:int,member_id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): mem=db.get(m.OrganizationMember,member_id); [setattr(mem,k,v) for k,v in payload.items() if hasattr(mem,k)]; db.commit(); return mem
@app.get('/brands')
def brands(u=Depends(user_from_auth),db:Session=Depends(get_db)): return user_brands(db,u)
@app.post('/brands')
def create_brand(data:BrandIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    b=m.Brand(**data.model_dump(), slug=data.name.lower().replace(' ','-')); db.add(b); db.commit(); return b
@app.get('/brands/{id}')
def brand(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.get(m.Brand,id)
@app.patch('/brands/{id}')
def patch_brand(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): b=db.get(m.Brand,id); [setattr(b,k,v) for k,v in payload.items() if hasattr(b,k)]; db.commit(); return b
@app.delete('/brands/{id}')
def del_brand(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): b=db.get(m.Brand,id); db.delete(b); db.commit(); return {'deleted':id}
@app.post('/brands/{id}/onboarding/complete')
def onboarding(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    b=db.get(m.Brand,id); dna=BrandAnalystAgent().run({**payload,'primary_language':b.primary_language}); row=m.BrandDNA(brand_id=id,voice_json=dna['voice'],visual_json=dna['visual'],compliance_json=dna['compliance'],channel_rules_json=dna['channel_rules'],cta_library_json={'items':dna['cta_library']},forbidden_words_json={'items':dna['forbidden_words']}); db.add(row)
    strat=ContentStrategistAgent().run(b,payload.get('goals',['awareness']))
    for p in strat['pillars']: db.add(m.ContentPillar(brand_id=id,**p))
    db.flush()
    for item in strat['calendar']: db.add(m.CalendarItem(brand_id=id,title=item['title'],description=item['description'],channels_json=item['channels'],content_type=item['content_type'],goal=item['goal'],language=b.primary_language,timezone=b.timezone))
    b.status='active'; db.commit(); return {'brand_id':id,'dna':dna,'calendar_items':7}
@app.get('/brands/{id}/dna')
def get_dna(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.BrandDNA).filter_by(brand_id=id).first()
@app.patch('/brands/{id}/dna')
def patch_dna(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): dna=db.query(m.BrandDNA).filter_by(brand_id=id).first(); [setattr(dna,k,v) for k,v in payload.items() if hasattr(dna,k)]; db.commit(); return dna
@app.get('/brands/{id}/memory')
def memory(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.BrandMemoryNote).filter_by(brand_id=id).all()
@app.post('/brands/{id}/memory')
def add_memory(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): note=m.BrandMemoryNote(brand_id=id,note=payload['note'],source_type=payload.get('source_type','manual'),auto_generated=False); db.add(note); db.commit(); return note
@app.patch('/brands/{id}/memory/{memory_id}')
def patch_memory(id:int,memory_id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): note=db.get(m.BrandMemoryNote,memory_id); [setattr(note,k,v) for k,v in payload.items() if hasattr(note,k)]; db.commit(); return note

@app.get('/workspace/current')
def current_workspace(u=Depends(user_from_auth),db:Session=Depends(get_db)):
    b=require_brand(db,u,None); org=db.get(m.Organization,b.organization_id) if b else None
    return {'user':{'id':u.id,'name':u.name,'email':u.email},'organization':({'id':org.id,'name':org.name} if org else None),'brand':({'id':b.id,'name':b.name,'primary_language':b.primary_language,'timezone':b.timezone} if b else None)}
@app.get('/calendar/overview')
def calendar_overview(brand_id:int|None=None, from_:str|None=Query(default=None, alias='from'), to:str|None=None, view:str='week', channel:str|None=None, status:str|None=None, content_type:str|None=None, campaign_id:int|None=None, owner:int|None=None, u=Depends(user_from_auth),db:Session=Depends(get_db)):
    b=require_brand(db,u,brand_id); org=db.get(m.Organization,b.organization_id) if b else None; now=datetime.now(timezone.utc)
    start=parse_dt(from_) or (now-timedelta(days=now.weekday())); end=parse_dt(to) or (start+(timedelta(days=31) if view=='month' else timedelta(days=7)))
    q=db.query(m.CalendarItem).filter_by(brand_id=b.id) if b else db.query(m.CalendarItem).filter(False)
    if view!='list': q=q.filter((m.CalendarItem.scheduled_at==None)|((m.CalendarItem.scheduled_at>=start)&(m.CalendarItem.scheduled_at<end)))
    rows=q.all()
    rows=[x for x in rows if (not channel or item_channel(x)==channel) and (not status or normalize_status(x.status)==status) and (not content_type or x.content_type==content_type) and (not campaign_id or x.campaign_id==campaign_id) and (not owner or (x.assigned_user_id or x.created_by_user_id)==owner)]
    accounts=db.query(m.ChannelAccount).filter_by(brand_id=b.id).all() if b else []; connected={a.provider:a.connection_status in ('connected','mock_connected','mock') for a in accounts}
    setup=setup_state(db,b); out=[calendar_item_out(x,db) for x in rows]; counts={s:len([i for i in out if i['status']==s]) for s in ['idea','draft','in_review','approved','scheduled','published','failed']}
    missing_dates=len([i for i in out if i['status'] in ('draft','approved') and not i['scheduled_at']])
    alerts=[]
    if not out: alerts.append({'id':'empty_week','title':'No content planned this week','description':'Create an item or generate a weekly plan.','severity':'warning','href':'/app/calendar'})
    if not accounts: alerts.append({'id':'no_channels','title':'Missing connected channels','description':'Connect a channel before publishing.','severity':'warning','href':'/app/integrations'})
    rec={'title':'Complete setup' if setup['missing_requirements'] else ('Plan your first content week' if not out else 'Review this week'),'description':'Resolve missing setup steps.' if setup['missing_requirements'] else ('Generate or create your first content items.' if not out else 'Keep 3–5 posts planned ahead.'),'action_label':'Complete setup' if setup['missing_requirements'] else ('Generate first week' if not out else 'View calendar'),'action_href':setup['missing_requirements'][0]['action_href'] if setup['missing_requirements'] else '/app/calendar','action_type':'navigate' if setup['missing_requirements'] else ('generate_week' if not out else 'navigate'),'severity':'warning' if setup['missing_requirements'] else 'info'}
    return {'user':{'id':u.id,'name':u.name,'email':u.email},'organization':({'id':org.id,'name':org.name} if org else None),'brand':({'id':b.id,'name':b.name,'primary_language':b.primary_language,'timezone':b.timezone} if b else None),'range':{'from':start.isoformat(),'to':end.isoformat(),'view':view,'timezone':b.timezone if b else u.timezone},'setup':setup,'items':out,'summary':{'total_items':len(out),'scheduled_count':counts['scheduled'],'draft_count':counts['draft'],'approval_pending_count':counts['in_review'],'published_count':counts['published'],'missing_dates_count':missing_dates},'filters':{'channels':[{'id':c,'label':c.replace('_',' ').title(),'connected':connected.get(c,False)} for c in ['instagram','telegram','bale','linkedin','google_business','tiktok','youtube','email','blog','other']],'statuses':[{'id':k,'label':k.replace('_',' ').title(),'count':counts.get(k,0)} for k in ['idea','draft','in_review','approved','scheduled','published','failed']],'content_types':[{'id':c,'label':c.replace('_',' ').title()} for c in ['post','reel','story','carousel','short_video','email','blog','google_update','telegram_post','bale_post']],'campaigns':[]},'recommended_action':rec,'alerts':alerts}
@app.post('/calendar/items')
def create_calendar_item(data:CalendarItemIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    b=require_brand(db,u,data.brand_id);
    if not b: raise HTTPException(422,'Create a brand before adding calendar items')
    if data.status=='published': raise HTTPException(422,'Published items must come from the publishing workflow')
    if data.status=='scheduled' and not data.scheduled_at: raise HTTPException(422,'scheduled_at is required for scheduled items')
    item=m.CalendarItem(brand_id=b.id,campaign_id=data.campaign_id,title=data.title.strip(),description=data.description or '',channels_json=[data.channel],content_type=data.content_type,status=data.status,scheduled_at=data.scheduled_at,timezone=data.timezone or b.timezone,language=b.primary_language,created_by_user_id=u.id,assigned_user_id=data.owner_user_id or u.id)
    db.add(item); db.commit(); db.refresh(item); return calendar_item_out(item,db)

@app.get('/brands/{id}/calendar')
def calendar(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    require_brand(db,u,id); return db.query(m.CalendarItem).filter_by(brand_id=id).all()
@app.post('/brands/{id}/calendar/items')
def add_item(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    require_brand(db,u,id); item=m.CalendarItem(brand_id=id,created_by_user_id=u.id,assigned_user_id=u.id,**payload); db.add(item); db.commit(); return item
def owned_item(db,u,id:int):
    item=db.get(m.CalendarItem,id)
    if not item: raise HTTPException(404,'Calendar item not found')
    require_brand(db,u,item.brand_id); return item
@app.patch('/calendar/items/{id}')
def patch_item(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    item=owned_item(db,u,id)
    if normalize_status(item.status)=='published': raise HTTPException(403,'Published items are read-only')
    if payload.get('status')=='published': raise HTTPException(422,'Published items must come from the publishing workflow')
    if payload.get('status')=='scheduled' and not (payload.get('scheduled_at') or item.scheduled_at): raise HTTPException(422,'scheduled_at is required for scheduled items')
    if 'channel' in payload: item.channels_json=[payload.pop('channel')]
    if 'owner_user_id' in payload: item.assigned_user_id=payload.pop('owner_user_id')
    if 'scheduled_at' in payload and payload['scheduled_at']: payload['scheduled_at']=parse_dt(payload['scheduled_at'])
    for k,v in payload.items():
        if hasattr(item,k): setattr(item,k,v)
    db.commit(); db.refresh(item); return calendar_item_out(item,db)
@app.delete('/calendar/items/{id}')
def delete_item(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    item=owned_item(db,u,id); db.delete(item); db.commit(); return {'deleted':id}
@app.post('/calendar/items/{id}/duplicate')
def duplicate_item(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    item=owned_item(db,u,id); copy=m.CalendarItem(brand_id=item.brand_id,campaign_id=item.campaign_id,title=item.title+' (copy)',description=item.description,channels_json=item.channels_json,content_type=item.content_type,status='idea',scheduled_at=None,timezone=item.timezone,language=item.language,created_by_user_id=u.id,assigned_user_id=u.id); db.add(copy); db.commit(); db.refresh(copy); return calendar_item_out(copy,db)
@app.post('/calendar/items/{id}/schedule')
def schedule_item(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    return patch_item(id,{'status':'scheduled','scheduled_at':payload.get('scheduled_at')},u,db)
@app.post('/calendar/items/{id}/move')
def move_item(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    return patch_item(id,{'scheduled_at':payload.get('scheduled_at')},u,db)
@app.post('/calendar/generate-week')
def gen_week_root(data:CalendarGenerateIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    b=require_brand(db,u,data.brand_id); setup=setup_state(db,b)
    if not b: raise HTTPException(422,'Create a brand before generating a calendar')
    if not setup['can_generate_week']: raise HTTPException(status_code=422, detail={'message':'Complete setup before generating a week','missing_requirements':setup['missing_requirements'],'action_links':setup['missing_requirements']})
    start=data.week_start or (datetime.now(timezone.utc)-timedelta(days=datetime.now(timezone.utc).weekday()))
    channels=data.channels or [a.provider for a in db.query(m.ChannelAccount).filter_by(brand_id=b.id).all()[:3]] or ['instagram']
    made=[]
    for i in range(7):
        ch=channels[i%len(channels)]; item=m.CalendarItem(brand_id=b.id,campaign_id=data.campaign_id,title=f'Draft content idea {i+1}',description=f'Draft weekly plan for {b.name}. Review before publishing.',channels_json=[ch],content_type='post',status='draft',scheduled_at=start+timedelta(days=i,hours=10),timezone=b.timezone,language=b.primary_language,created_by_user_id=u.id,assigned_user_id=u.id); db.add(item); db.flush(); made.append(item)
    db.commit(); return {'items':[calendar_item_out(x,db) for x in made]}
@app.post('/brands/{id}/calendar/generate-week')
def gen_week(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return gen_week_root(CalendarGenerateIn(brand_id=id),u,db)
@app.post('/brands/{id}/calendar/regenerate-week')
def regen_week(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return gen_week(id,u,db)
@app.get('/brands/{id}/drafts')
def drafts(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.ContentDraft).filter_by(brand_id=id).all()
@app.post('/calendar/items/{id}/generate-drafts')
def gen_drafts(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    item=db.get(m.CalendarItem,id); dna=db.query(m.BrandDNA).filter_by(brand_id=item.brand_id).first(); made=[]
    for ch in item.channels_json[:3]:
        out=CopywriterAgent().run(item,dna,ch,item.language); d=m.ContentDraft(calendar_item_id=id,brand_id=item.brand_id,channel=ch,content_type=item.content_type,language=item.language,title=out['title'],body=out['body'],hashtags_json=out['hashtags'],brand_fit_score=out['brand_fit_score'],compliance_score=out['compliance_score'],created_by_user_id=u.id); db.add(d); db.flush(); v=m.ContentVersion(draft_id=d.id,version_number=1,title=d.title,body=d.body,created_by_user_id=u.id); db.add(v); db.flush(); d.current_version_id=v.id; made.append(d.id)
    item.status='draft_ready'; db.commit(); return {'draft_ids':made}
@app.get('/drafts/{id}')
def draft(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.get(m.ContentDraft,id)
@app.patch('/drafts/{id}')
def patch_draft(id:int,data:DraftPatch,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); [setattr(d,k,v) for k,v in data.model_dump(exclude_none=True).items()]; db.flush(); v=m.ContentVersion(draft_id=id,version_number=db.query(m.ContentVersion).filter_by(draft_id=id).count()+1,title=d.title,body=d.body,created_by_user_id=u.id,ai_generated=False); db.add(v); db.commit(); return d
@app.post('/drafts/{id}/revise')
def revise(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); d.body += '\n\nRevision: '+payload.get('prompt','Make it better'); db.commit(); return d
@app.post('/drafts/{id}/translate')
def translate(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); d.language=payload.get('language','en'); d.body=f"[{d.language}] {d.body}"; db.commit(); return d
@app.post('/drafts/{id}/compliance-check')
def compliance(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); return {'risk_score':float(d.compliance_score),'warnings':[]}
@app.get('/drafts/{id}/versions')
def versions(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.ContentVersion).filter_by(draft_id=id).all()
@app.post('/drafts/{id}/approval-requests')
def approval_req(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): tok=token_urlsafe(24); ar=m.ApprovalRequest(draft_id=id,requested_by_user_id=u.id,public_token_hash=sha256(tok.encode()).hexdigest()); db.add(ar); db.commit(); return {'id':ar.id,'public_url':f'/public/approval/{tok}','token':tok}
@app.get('/approvals')
def approvals(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.ApprovalRequest).all()
@app.get('/approvals/{id}')
def approval(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.get(m.ApprovalRequest,id)
def do_action(ar, data, db, user_id=None, source='in_app'):
    ar.status={'approve':'approved','reject':'rejected','request_changes':'changes_requested'}.get(data.action,data.action); aa=m.ApprovalAction(approval_request_id=ar.id,user_id=user_id,action=data.action,comment=data.comment,revision_prompt=data.revision_prompt,save_to_memory=data.save_to_memory,source_channel=source); db.add(aa); db.flush();
    if data.save_to_memory: db.add(m.BrandMemoryNote(brand_id=db.get(m.ContentDraft,ar.draft_id).brand_id,note=ApprovalLearningAgent().run(aa)['note'],source_type='approval',source_id=str(aa.id)))
    db.commit(); return {'status':ar.status}
@app.post('/approvals/{id}/approve')
def approve(id:int,data:ActionIn=ActionIn(action='approve'),u=Depends(user_from_auth),db:Session=Depends(get_db)): return do_action(db.get(m.ApprovalRequest,id),ActionIn(action='approve',comment=data.comment),db,u.id)
@app.post('/approvals/{id}/reject')
def reject(id:int,data:ActionIn,u=Depends(user_from_auth),db:Session=Depends(get_db)): data.action='reject'; return do_action(db.get(m.ApprovalRequest,id),data,db,u.id)
@app.post('/approvals/{id}/request-changes')
def req_changes(id:int,data:ActionIn,u=Depends(user_from_auth),db:Session=Depends(get_db)): data.action='request_changes'; return do_action(db.get(m.ApprovalRequest,id),data,db,u.id)
@app.get('/public/approval/{token}')
def public_approval(token:str,db:Session=Depends(get_db)): ar=db.query(m.ApprovalRequest).filter_by(public_token_hash=sha256(token.encode()).hexdigest()).first(); d=db.get(m.ContentDraft,ar.draft_id) if ar else None; return {'approval':ar,'draft':d}
@app.post('/public/approval/{token}/action')
def public_action(token:str,data:ActionIn,db:Session=Depends(get_db)): ar=db.query(m.ApprovalRequest).filter_by(public_token_hash=sha256(token.encode()).hexdigest()).first(); return do_action(ar,data,db,None,'public_link')
@app.get('/brands/{id}/channel-accounts')
def accounts(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.ChannelAccount).filter_by(brand_id=id).all()
@app.post('/brands/{id}/connectors/{provider}/connect')
def connect(id:int,provider:str,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    c=get_connector(provider); creds=payload.get('credentials',payload); has_creds=bool(creds.get('token') or creds.get('api_key') or creds.get('consumer_key') or creds.get('service_account_json'))
    assisted={'instagram','tiktok','linkedin','google_business'}; status='connected' if has_creds and provider not in assisted else ('requires_api_review' if has_creds and provider in assisted else ('mock' if DEMO_MODE and payload.get('mock') else 'needs_credentials'))
    acc=db.query(m.ChannelAccount).filter_by(brand_id=id,provider=provider).first() or m.ChannelAccount(brand_id=id,provider=provider,account_name=payload.get('account_name',provider),account_identifier=payload.get('account_identifier','needs_credentials'))
    acc.capabilities_json=c.capabilities.__dict__; acc.credentials_encrypted_json={k:('********' if 'secret' in k or 'token' in k else v) for k,v in creds.items()}; acc.connection_status=status
    db.add(acc); db.commit(); return acc
@app.get('/connectors/{provider}/callback')
def cb(provider:str): return {'provider':provider,'status':'oauth_placeholder'}
@app.post('/drafts/{id}/publish-now')
def publish(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); acc=db.query(m.ChannelAccount).filter_by(brand_id=d.brand_id,provider=d.channel).first() or db.query(m.ChannelAccount).filter_by(brand_id=d.brand_id).first(); res=get_connector(acc.provider if acc else 'mock').publish_post(d,acc); pp=m.PublishedPost(draft_id=id,channel_account_id=acc.id if acc else 1,provider_post_id=res.get('provider_post_id','assisted'),public_url=res.get('public_url',res.get('assisted_publish_url','/assisted'))); db.add(pp); db.commit(); return {'result':res,'published_post_id':pp.id}
@app.post('/drafts/{id}/schedule')
def schedule(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); acc=db.query(m.ChannelAccount).filter_by(brand_id=d.brand_id).first(); sp=m.ScheduledPost(draft_id=id,channel_account_id=acc.id,scheduled_at=datetime.now(timezone.utc),status='scheduled'); db.add(sp); db.commit(); return sp
@app.get('/scheduled-posts/{id}/assisted-kit')
def kit(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): sp=db.get(m.ScheduledPost,id); d=db.get(m.ContentDraft,sp.draft_id); return {'caption':d.body,'hashtags':d.hashtags_json,'checklist':['Download media','Copy caption','Open platform','Paste and publish','Mark manually published']}
@app.post('/scheduled-posts/{id}/retry')
def retry(id:int,u=Depends(user_from_auth)): return {'status':'retry_queued'}
@app.post('/scheduled-posts/{id}/mark-manual-published')
def manual(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): sp=db.get(m.ScheduledPost,id); sp.status='published'; db.commit(); return sp
@app.post('/webhooks/telegram/{brand_id}')
def wh_t(brand_id:int,payload:dict): return {'processed':True,'provider':'telegram'}
@app.post('/webhooks/bale/{brand_id}')
def wh_b(brand_id:int,payload:dict): return {'processed':True,'provider':'bale'}
@app.post('/webhooks/bale-safir/{brand_id}')
def wh_bs(brand_id:int,payload:dict): return {'processed':True,'provider':'bale_safir'}
@app.post('/connectors/telegram/poll')
def poll_t(): return {'updates':[]}
@app.post('/connectors/bale/poll')
def poll_b(): return {'updates':[]}
@app.post('/brands/{id}/connectors/bale/test-message')
def bale_test(id:int,payload:dict,u=Depends(user_from_auth)): return get_connector('bale').send_message(payload.get('chat_id','mock'),payload.get('text','Test'))
@app.post('/brands/{id}/connectors/bale/set-webhook')
def bale_set(id:int,payload:dict,u=Depends(user_from_auth)): return {'webhook_set':payload.get('url')}
@app.post('/brands/{id}/connectors/bale/delete-webhook')
def bale_del(id:int,u=Depends(user_from_auth)): return {'webhook_deleted':True}
@app.post('/brands/{id}/connectors/bale/get-updates')
def bale_updates(id:int,u=Depends(user_from_auth)): return {'updates':[]}
@app.post('/drafts/{id}/publish-bale')
def pub_bale(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return publish(id,u,db)
@app.post('/approvals/{id}/send-bale')
def send_bale(id:int,u=Depends(user_from_auth)): return {'sent':True,'inline_buttons':['Approve','Edit with prompt','Reject','Open preview']}
@app.post('/brands/{id}/connectors/bale-safir/connect')
def connect_safir(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): return connect(id,'bale_safir',payload,u,db)
@app.post('/brands/{id}/connectors/bale-safir/test-message')
def test_safir(id:int,payload:dict,u=Depends(user_from_auth)): return get_connector('bale_safir').send_message(payload.get('phone_number'), {'text':payload.get('text','Test')}, payload, consent=payload.get('consent',False))
@app.post('/messages/bale-safir/send')
def safir_send(payload:dict,u=Depends(user_from_auth)): return get_connector('bale_safir').send_message(payload.get('phone_number'), payload.get('message_data',{}), payload.get('credentials',{}), consent=payload.get('consent',False))
@app.get('/messages/bale-safir/{message_id}')
def safir_msg(message_id:str,u=Depends(user_from_auth)): return {'message_id':message_id,'status':'delivered_mock'}
@app.post('/published-posts/{id}/fetch-insights')
def insights(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): snap=m.InsightSnapshot(published_post_id=id,metrics_json=get_connector('mock').fetch_analytics(id),normalized_scores_json={'awareness_score':82,'engagement_score':74,'conversion_score':48}); db.add(snap); db.commit(); return snap
@app.get('/brands/{id}/analytics/overview')
def analytics(id:int,u=Depends(user_from_auth)): return {'awareness_score':82,'engagement_score':74,'best_channel':'mock','revenue':1200}
@app.get('/brands/{id}/reports/weekly')
def reports(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.WeeklyReport).filter_by(brand_id=id).all()
@app.post('/brands/{id}/reports/generate-weekly')
def gen_report(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): rep=m.WeeklyReport(brand_id=id,week_start='2026-06-29',week_end='2026-07-05',summary='Mock weekly report: approvals and CTA-led posts improved performance.',insights_json=PerformanceAnalystAgent().run({'orders':1}),recommendations_json={'next_week':['More platform-native variants']}); db.add(rep); db.commit(); return rep
@app.get('/brands/{id}/assets')
def assets(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.Asset).filter_by(brand_id=id).all()
@app.post('/brands/{id}/assets')
def create_asset(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): row=m.Asset(brand_id=id,name=payload.get('name','Untitled asset'),asset_type=payload.get('asset_type','metadata_only'),url=payload.get('url'),description=payload.get('description','Metadata-only placeholder asset'),tags_json=payload.get('tags',[]),metadata_json=payload); db.add(row); db.commit(); return row
@app.patch('/assets/{id}')
def patch_asset(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): row=db.get(m.Asset,id); [setattr(row,k,v) for k,v in payload.items() if hasattr(row,k)]; db.commit(); return row
@app.delete('/assets/{id}')
def del_asset(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): row=db.get(m.Asset,id); db.delete(row); db.commit(); return {'deleted':id}
@app.get('/brands/{id}/campaigns')
def campaigns(id:int,u=Depends(user_from_auth)): return []
@app.post('/brands/{id}/campaigns')
def create_campaign(id:int,payload:dict,u=Depends(user_from_auth)): return {'id':'campaign_mock','brand_id':id,**payload}
@app.get('/campaigns/{id}')
def campaign(id:str,u=Depends(user_from_auth)): return {'id':id,'status':'planned'}
@app.patch('/campaigns/{id}')
def patch_campaign(id:str,payload:dict,u=Depends(user_from_auth)): return {'id':id,**payload}
@app.post('/campaigns/{id}/generate-plan')
def campaign_plan(id:str,u=Depends(user_from_auth)): return {'campaign_id':id,'plan':['strategy','calendar','drafts','tracking links']}
@app.get('/admin/overview')
def admin_overview(u=Depends(user_from_auth),db:Session=Depends(get_db)): return {'organizations':db.query(m.Organization).count(),'brands':db.query(m.Brand).count(),'users':db.query(m.User).count(),'published_posts':db.query(m.PublishedPost).count(),'failed_jobs':db.query(m.JobLog).filter_by(status='failed').count(),'connector_errors':0,'pending_approvals':db.query(m.ApprovalRequest).filter_by(status='pending').count()}
@app.get('/admin/organizations')
def admin_orgs(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.Organization).all()
@app.patch('/admin/organizations/{id}')
def admin_org_patch(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): return patch_org(id,payload,u,db)
@app.get('/admin/users')
def admin_users(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.User).all()
@app.patch('/admin/users/{id}')
def admin_user_patch(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): user=db.get(m.User,id); [setattr(user,k,v) for k,v in payload.items() if hasattr(user,k)]; db.commit(); return user
@app.get('/admin/brands')
def admin_brands(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.Brand).all()
@app.get('/admin/ai-usage')
def ai_usage(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.AIUsageLog).all()
@app.get('/admin/jobs')
def jobs(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.JobLog).all()
@app.post('/admin/jobs/{id}/retry')
def job_retry(id:int,u=Depends(user_from_auth)): return {'job_id':id,'status':'retry_queued'}
@app.get('/admin/connectors')
def conns(u=Depends(user_from_auth)): return connector_catalog()
@app.patch('/admin/connectors/{provider}')
def conn_patch(provider:str,payload:dict,u=Depends(user_from_auth)): return {'provider':provider,'updated':payload}
@app.get('/admin/audit-logs')
def audits(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.AuditLog).all()
@app.get('/admin/plans')
def plans(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.Plan).all()
@app.post('/admin/plans')
def plan(payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): p=m.Plan(**payload); db.add(p); db.commit(); return p
@app.patch('/admin/plans/{id}')
def patch_plan(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): p=db.get(m.Plan,id); [setattr(p,k,v) for k,v in payload.items() if hasattr(p,k)]; db.commit(); return p
@app.get('/admin/feature-flags')
def flags(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.FeatureFlag).all()
@app.patch('/admin/feature-flags/{id}')
def patch_flag(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): f=db.get(m.FeatureFlag,id); [setattr(f,k,v) for k,v in payload.items() if hasattr(f,k)]; db.commit(); return f

# --- Real Product + Light UI v4 additive endpoints ---
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'

@app.get('/environment')
def environment(): return {'demo_mode': DEMO_MODE, 'mode': 'Demo mode' if DEMO_MODE else 'Production mode'}

@app.get('/onboarding/status')
def onboarding_status(u=Depends(user_from_auth), db:Session=Depends(get_db)):
    brands=db.query(m.Brand).all(); brand=brands[0] if brands else None
    return {'completed': bool(brand and brand.status=='active'), 'brand_id': brand.id if brand else None, 'steps': db.query(m.SetupChecklistItem).filter_by(brand_id=brand.id).all() if brand else []}

@app.post('/onboarding/save-step')
def onboarding_save_step(payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    org_data=payload.get('organization') or {}; brand_data=payload.get('brand') or {}; brand_id=payload.get('brand_id')
    org=None; brand=db.get(m.Brand,brand_id) if brand_id else None
    if org_data:
        org=db.get(m.Organization,org_data.get('id')) if org_data.get('id') else None
        if not org:
            org=m.Organization(name=org_data.get('name','New organization'),slug=(org_data.get('name','new-organization').lower().replace(' ','-')),mode=org_data.get('mode','owner'),owner_user_id=u.id); db.add(org); db.flush(); db.add(m.OrganizationMember(organization_id=org.id,user_id=u.id,role='org_owner'))
        else:
            [setattr(org,k,v) for k,v in org_data.items() if hasattr(org,k)]
    if brand_data:
        if not org: org=db.query(m.Organization).filter_by(owner_user_id=u.id).first()
        if not brand:
            brand=m.Brand(organization_id=brand_data.get('organization_id') or (org.id if org else None),name=brand_data.get('name','New brand'),slug=brand_data.get('name','new-brand').lower().replace(' ','-'),industry=brand_data.get('industry','general'),country=brand_data.get('country','DE'),primary_language=brand_data.get('primary_language','en'),timezone=brand_data.get('timezone','UTC'),description=brand_data.get('description',''))
            db.add(brand); db.flush()
        else:
            [setattr(brand,k,v) for k,v in brand_data.items() if hasattr(brand,k)]
    db.commit(); return {'organization_id': org.id if org else None, 'brand_id': brand.id if brand else brand_id, 'saved': True}

@app.post('/onboarding/complete')
def onboarding_complete(payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    saved=onboarding_save_step(payload,u,db); brand_id=saved.get('brand_id') or payload.get('brand_id')
    brand=db.get(m.Brand,brand_id)
    if not brand: raise HTTPException(400,'Brand is required')
    dna=db.query(m.BrandDNA).filter_by(brand_id=brand.id).first() or m.BrandDNA(brand_id=brand.id); db.add(dna)
    dna.voice_json=payload.get('voice',payload.get('brand_voice',{'tone':'clear'})); dna.channel_rules_json=payload.get('channel_rules',{}); dna.compliance_json=payload.get('approval_settings',{}); dna.cta_library_json={'items':payload.get('ctas',['Learn more'])}; dna.forbidden_words_json={'items':payload.get('forbidden_words',[])}
    db.query(m.ProductService).filter_by(brand_id=brand.id).delete();
    for ps in payload.get('products_services',payload.get('products',[])) or []: db.add(m.ProductService(brand_id=brand.id,type=ps.get('type','service'),name=ps.get('name','Offer'),description=ps.get('description',''),metadata_json=ps))
    for provider in payload.get('channels',payload.get('channel_preferences',['instagram','linkedin'])): 
        if not db.query(m.ChannelAccount).filter_by(brand_id=brand.id,provider=provider).first(): db.add(m.ChannelAccount(brand_id=brand.id,provider=provider,account_name=provider,account_identifier='needs_credentials',connection_status='needs_credentials',capabilities_json=get_connector(provider).capabilities.__dict__ if provider in [c['provider'] for c in connector_catalog()] else {},credentials_encrypted_json={}))
    for name in payload.get('content_goals',payload.get('pillars',['Education','Proof','Offer'])):
        if not db.query(m.ContentPillar).filter_by(brand_id=brand.id,name=str(name)).first(): db.add(m.ContentPillar(brand_id=brand.id,name=str(name),description='Onboarding content pillar'))
    for key,label in [('profile','Brand profile'),('dna','Brand voice'),('channels','Channels'),('approval','Approvals')]:
        row=db.query(m.SetupChecklistItem).filter_by(brand_id=brand.id,key=key).first() or m.SetupChecklistItem(brand_id=brand.id,key=key,label=label); row.status='done'; db.add(row)
    brand.status='active'; db.commit(); return {'completed':True,'brand_id':brand.id}

@app.get('/brands/{id}/setup-checklist')
def setup_checklist(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.SetupChecklistItem).filter_by(brand_id=id).all()
@app.patch('/brands/{id}/setup-checklist/{item_id}')
def setup_checklist_patch(id:int,item_id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): row=db.get(m.SetupChecklistItem,item_id); [setattr(row,k,v) for k,v in payload.items() if hasattr(row,k)]; db.commit(); return row

@app.get('/brands/{id}/dashboard')
def dashboard(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    items=db.query(m.CalendarItem).filter_by(brand_id=id).all(); drafts=db.query(m.ContentDraft).filter_by(brand_id=id).all(); accounts=db.query(m.ChannelAccount).filter_by(brand_id=id).all(); approvals_list=db.query(m.ApprovalRequest).join(m.ContentDraft,m.ContentDraft.id==m.ApprovalRequest.draft_id).filter(m.ContentDraft.brand_id==id).all()
    done=db.query(m.SetupChecklistItem).filter_by(brand_id=id,status='done').count(); total=max(db.query(m.SetupChecklistItem).filter_by(brand_id=id).count(),4)
    return {'setup_completion':round(done/total*100),'next_best_action':'Generate this week' if not items else 'Review pending approvals','pipeline_counts':{s:len([d for d in drafts if d.status==s]) for s in ['draft_ready','in_approval','approved','rejected']},'today_tasks':items[:5],'secondary_metrics':{'drafts':len(drafts),'calendar_items':len(items),'approvals':len(approvals_list)},'approval_queue':approvals_list,'brand_memory_notes':db.query(m.BrandMemoryNote).filter_by(brand_id=id).all(),'connector_health':[{'provider':a.provider,'status':a.connection_status} for a in accounts],'weekly_insight':(db.query(m.WeeklyReport).filter_by(brand_id=id).first().summary if db.query(m.WeeklyReport).filter_by(brand_id=id).first() else 'No weekly report yet')}

@app.post('/brands/{id}/drafts')
def create_draft(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d=m.ContentDraft(brand_id=id,calendar_item_id=payload.get('calendar_item_id'),channel=payload.get('channel','assisted'),content_type=payload.get('content_type','post'),language=payload.get('language','en'),title=payload.get('title','Untitled draft'),body=payload.get('body',''),created_by_user_id=u.id); db.add(d); db.flush(); v=m.ContentVersion(draft_id=d.id,version_number=1,title=d.title,body=d.body,created_by_user_id=u.id,ai_generated=False); db.add(v); db.flush(); d.current_version_id=v.id; db.commit(); return d
@app.post('/drafts/{id}/versions')
def create_version(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): d=db.get(m.ContentDraft,id); v=m.ContentVersion(draft_id=id,version_number=db.query(m.ContentVersion).filter_by(draft_id=id).count()+1,title=payload.get('title',d.title),body=payload.get('body',d.body),metadata_json=payload.get('metadata',{}),created_by_user_id=u.id,ai_generated=payload.get('ai_generated',False)); db.add(v); d.title=v.title; d.body=v.body; db.flush(); d.current_version_id=v.id; db.commit(); return v
@app.get('/brands/{id}/approvals')
def brand_approvals(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.ApprovalRequest).join(m.ContentDraft,m.ContentDraft.id==m.ApprovalRequest.draft_id).filter(m.ContentDraft.brand_id==id).all()

@app.patch('/channel-accounts/{id}')
def patch_account(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): acc=db.get(m.ChannelAccount,id); [setattr(acc,k,v) for k,v in payload.items() if hasattr(acc,k)]; db.commit(); return acc
@app.post('/channel-accounts/{id}/test')
def test_account(id:int,payload:dict={},u=Depends(user_from_auth),db:Session=Depends(get_db)):
    acc=db.get(m.ChannelAccount,id); creds={**(acc.credentials_encrypted_json or {}),**payload}; ok=bool(creds.get('token') or creds.get('api_key') or creds.get('consumer_key') or creds.get('service_account_json'))
    acc.connection_status='connected' if ok else ('mock' if DEMO_MODE and (acc.credentials_encrypted_json or {}).get('mock') else 'needs_credentials'); acc.last_sync_at=datetime.now(timezone.utc) if ok else acc.last_sync_at; db.commit(); return {'ok':ok,'status':acc.connection_status,'message':'Credentials validated' if ok else 'Needs credentials'}
@app.post('/channel-accounts/{id}/disconnect')
def disconnect_account(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): acc=db.get(m.ChannelAccount,id); acc.connection_status='needs_credentials'; acc.credentials_encrypted_json={}; db.commit(); return acc

@app.post('/brands/{id}/analytics/manual-entry')
def manual_metric(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): row=m.ManualMetric(brand_id=id,metric_date=payload.get('metric_date',datetime.now(timezone.utc).date().isoformat()),metrics_json=payload.get('metrics',payload)); db.add(row); db.commit(); return row

# --- Tenant-aware Content Studio endpoints ---
from typing import Any
class StudioDraftIn(BaseModel):
    title:str|None=None; body:str|None=None; hook:str|None=None; cta:str|None=None; hashtags:str|list[str]|None=None
    goal:str|None=None; channel:str|None=None; language:str|None=None; content_type:str|None=None; product_or_offer:str|None=None; tone:str|None=None; prompt:str|None=None; status:str|None=None
class StudioGenerateIn(BaseModel):
    goal:str; channel:str; language:str='en'; content_type:str='post'; product_or_offer:str=''; tone:str='clear'; prompt:str
class StudioTransformIn(BaseModel): action:str; target_language:str|None=None
class StudioScheduleIn(BaseModel): date:str; time:str; timezone:str='UTC'; channel:str|None=None

def _studio_error(status:int, code:str, message:str, details:Any=None):
    raise HTTPException(status_code=status, detail={'error':{'code':code,'message':message,'details':details or {}}})
def _user_org_brand(u, db):
    mem=db.query(m.OrganizationMember).filter_by(user_id=u.id,status='active').first()
    org=db.get(m.Organization,mem.organization_id) if mem else db.query(m.Organization).filter_by(owner_user_id=u.id).first()
    brand=db.query(m.Brand).filter_by(organization_id=org.id).first() if org else None
    return org, brand

def _assert_draft(draft_id:int,u,db):
    d=db.get(m.ContentDraft,draft_id)
    if not d: _studio_error(404,'draft_not_found','Draft not found')
    org,brand=_user_org_brand(u,db)
    if not brand or d.brand_id!=brand.id: _studio_error(403,'wrong_tenant','Draft belongs to another workspace')
    return d,org,brand

def _meta(d):
    if not d.current_version_id: return {}
    v=db_global.query(m.ContentVersion).filter_by(id=d.current_version_id).first() if False else None
    return {}

def _draft_json(d, db=None):
    meta={}
    if db and d.current_version_id:
        v=db.get(m.ContentVersion,d.current_version_id); meta=(v.metadata_json or {}) if v else {}
    return {'id':d.id,'brand_id':d.brand_id,'title':d.title or '','body':d.body or '','hook':meta.get('hook',''),'cta':meta.get('cta',''),'hashtags':' '.join(d.hashtags_json or meta.get('hashtags',[]) or []),'goal':meta.get('goal',''),'channel':d.channel,'language':d.language,'content_type':d.content_type,'product_or_offer':meta.get('product_or_offer',''),'tone':meta.get('tone',''),'prompt':meta.get('prompt',''),'status':('draft' if d.status=='draft_ready' else d.status),'quality_score':float(d.brand_fit_score or 0),'warnings':meta.get('warnings',[]),'compliance_result':meta.get('compliance_result'),'updated_at':d.updated_at.isoformat() if hasattr(d.updated_at,'isoformat') else str(d.updated_at)}

def _brand_rules(brand, db):
    dna=db.query(m.BrandDNA).filter_by(brand_id=brand.id).first() if brand else None
    if not dna: return []
    rules=[]
    tone=(dna.voice_json or {}).get('tone') or (dna.voice_json or {}).get('personality')
    if tone: rules.append({'id':'tone','label':'Allowed tone','description':str(tone),'severity':'info'})
    for w in (dna.forbidden_words_json or {}).get('items',[])[:8]: rules.append({'id':'forbidden-'+str(w),'label':'Forbidden phrase','description':str(w),'severity':'danger'})
    if dna.compliance_json: rules.append({'id':'approval','label':'Approval notes','description':str(dna.compliance_json),'severity':'warning'})
    if dna.channel_rules_json: rules.append({'id':'channels','label':'Channel rules','description':str(dna.channel_rules_json),'severity':'info'})
    return rules

def _missing(brand, db):
    miss=[]
    if not brand or brand.status!='active': miss.append({'id':'brand_pulse','title':'Brand Pulse incomplete','action_href':'/onboarding'})
    if brand and db.query(m.ProductService).filter_by(brand_id=brand.id).count()==0: miss.append({'id':'product','title':'No product/service','action_href':'/onboarding'})
    if brand and db.query(m.ChannelAccount).filter_by(brand_id=brand.id).count()==0: miss.append({'id':'channels','title':'No channels selected','action_href':'/app/integrations'})
    if brand and not db.query(m.ChannelAccount).filter(m.ChannelAccount.brand_id==brand.id,m.ChannelAccount.provider.in_(['telegram','bale','email','approval_link'])).first(): miss.append({'id':'approval','title':'No approval method','action_href':'/app/integrations'})
    return miss

def _save_version(d, db, u, meta, ai=True):
    v=m.ContentVersion(draft_id=d.id,version_number=db.query(m.ContentVersion).filter_by(draft_id=d.id).count()+1,title=d.title,body=d.body,metadata_json=meta,created_by_user_id=u.id,ai_generated=ai); db.add(v); db.flush(); d.current_version_id=v.id

def _apply_payload(d,p):
    data=p.model_dump(exclude_none=True) if hasattr(p,'model_dump') else p
    d.title=data.get('title',d.title) or 'Untitled draft'; d.body=data.get('body',d.body) or ''; d.channel=data.get('channel',d.channel or 'instagram'); d.language=data.get('language',d.language or 'en'); d.content_type=data.get('content_type',d.content_type or 'post'); d.status=data.get('status',d.status or 'draft')
    hs=data.get('hashtags')
    if isinstance(hs,str): d.hashtags_json=[x for x in hs.split() if x]
    elif isinstance(hs,list): d.hashtags_json=hs
    return data

@app.get('/studio/overview')
def studio_overview(u=Depends(user_from_auth),db:Session=Depends(get_db)):
    org,brand=_user_org_brand(u,db); drafts=db.query(m.ContentDraft).filter_by(brand_id=brand.id).order_by(m.ContentDraft.updated_at.desc()).limit(20).all() if brand else []
    miss=_missing(brand,db); rec={'title':'Generate first draft','description':'Start from your brief and Brand Pulse.','action_label':'Generate first draft','action_type':'generate'} if not drafts else {'title':'Run compliance check','description':'Check the active draft before approval.','action_label':'Compliance check','action_type':'check'}
    return {'user':{'id':u.id,'name':u.name,'email':u.email},'organization':({'id':org.id,'name':org.name} if org else None),'brand':({'id':brand.id,'name':brand.name,'primary_language':brand.primary_language,'industry':brand.industry} if brand else None),'setup':{'can_generate':bool(brand and not any(x['id']=='brand_pulse' for x in miss)),'missing_requirements':miss},'drafts':[_draft_json(d,db) for d in drafts],'brand_rules':_brand_rules(brand,db),'recommended_action':rec,'products':[p.name for p in (db.query(m.ProductService).filter_by(brand_id=brand.id).all() if brand else [])],'channels':[a.provider for a in (db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all() if brand else [])]}
@app.get('/studio/drafts')
def studio_drafts(u=Depends(user_from_auth),db:Session=Depends(get_db)):
    org,brand=_user_org_brand(u,db); return [_draft_json(d,db) for d in (db.query(m.ContentDraft).filter_by(brand_id=brand.id).order_by(m.ContentDraft.updated_at.desc()).all() if brand else [])]
@app.get('/studio/drafts/{id}')
def studio_get_draft(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): d,_,_=_assert_draft(id,u,db); return _draft_json(d,db)
@app.post('/studio/drafts')
def studio_create_draft(payload:StudioDraftIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    org,brand=_user_org_brand(u,db)
    if not brand: _studio_error(422,'missing_brand','Create a brand before drafting')
    d=m.ContentDraft(brand_id=brand.id,channel=payload.channel or 'instagram',content_type=payload.content_type or 'post',language=payload.language or brand.primary_language or 'en',title=payload.title or 'Untitled draft',body=payload.body or '',created_by_user_id=u.id,status=payload.status or 'draft'); db.add(d); db.flush(); meta=_apply_payload(d,payload); _save_version(d,db,u,meta,False); db.commit(); return _draft_json(d,db)
@app.patch('/studio/drafts/{id}')
def studio_patch_draft(id:int,payload:StudioDraftIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d,_,_=_assert_draft(id,u,db)
    if d.status=='published': _studio_error(409,'published_read_only','Published drafts are read-only')
    meta=_apply_payload(d,payload); _save_version(d,db,u,meta,False); db.commit(); return _draft_json(d,db)
@app.delete('/studio/drafts/{id}')
def studio_delete_draft(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): d,_,_=_assert_draft(id,u,db); d.status='archived'; db.commit(); return {'deleted':id}
@app.post('/studio/generate')
def studio_generate(payload:StudioGenerateIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    org,brand=_user_org_brand(u,db)
    if not brand: _studio_error(422,'missing_brand','Create Brand Pulse before generation')
    if not payload.goal or not payload.channel or not payload.prompt: _studio_error(422,'validation_error','Goal, channel, and prompt are required')
    name=brand.name; offer=payload.product_or_offer or 'your offer'; hook=f"{offer}: {payload.goal}"; title=f"{payload.content_type.title()} for {offer}"; cta='Book a consultation' if any(x in (offer+payload.prompt).lower() for x in ['clinic','medical','botox','esthetic']) else 'Contact us to learn more'
    body=f"{hook}\n\n{payload.prompt}\n\nHere is a {payload.tone} {payload.channel} message from {name} about {offer}. It explains the value clearly, keeps the promise realistic, and invites the audience to take the next step.\n\n{cta}"
    hs=[f"#{name.replace(' ','')[:20]}", '#SmarbizDraft', f"#{payload.channel}"]
    warnings=[]
    d=m.ContentDraft(brand_id=brand.id,channel=payload.channel,content_type=payload.content_type,language=payload.language,title=title,body=body,hashtags_json=hs,status='draft',brand_fit_score=.82,compliance_score=.74,ai_provider=settings.ai_provider,created_by_user_id=u.id); db.add(d); db.flush(); meta={**payload.model_dump(),'hook':hook,'cta':cta,'hashtags':hs,'warnings':warnings,'provider':settings.ai_provider}; _save_version(d,db,u,meta,True); db.commit(); return {'draft':_draft_json(d,db),'provider':settings.ai_provider,'warnings':warnings}
@app.post('/studio/drafts/{id}/transform')
def studio_transform(id:int,payload:StudioTransformIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d,_,_=_assert_draft(id,u,db); meta=(db.get(m.ContentVersion,d.current_version_id).metadata_json or {}) if d.current_version_id else {}; action=payload.action
    if action=='shorten': d.body=d.body[:420].rstrip()+('…' if len(d.body)>420 else '')
    elif action=='more_formal': d.body='In a professional tone: '+d.body; meta['tone']='formal'
    elif action=='more_direct': d.body=d.body+'\n\nTake the next step today.'; meta['cta']='Take the next step today.'
    elif action=='translate':
        if not payload.target_language: _studio_error(422,'missing_target_language','Choose English, Persian, or German')
        d.language=payload.target_language; d.body=f"[{payload.target_language}] {d.body}"
    else: d.body=d.body+'\n\nRewritten for clarity while preserving the original intent.'
    _save_version(d,db,u,meta,True); db.commit(); return _draft_json(d,db)
@app.post('/studio/drafts/{id}/compliance-check')
def studio_compliance(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d,_,brand=_assert_draft(id,u,db); text=(d.title+' '+d.body).lower(); warnings=[]; suggestions=[]
    if not ((db.get(m.ContentVersion,d.current_version_id).metadata_json or {}).get('cta') if d.current_version_id else ''): warnings.append({'id':'missing_cta','title':'Missing CTA','description':'Add a clear next step.','severity':'warning'}); suggestions.append('Add a clear CTA.')
    for term in ['guaranteed','cure','risk-free','always','never']:
        if term in text: warnings.append({'id':'absolute_'+term,'title':'Absolute claim','description':f'Avoid unsupported absolute claim: {term}.','severity':'danger'}); suggestions.append('Use qualified, evidence-aware wording.')
    if any(x in text for x in ['botox','clinic','medical','treatment','esthetic']): suggestions.append('Use consultation-first wording and avoid guaranteed results.')
    result={'status':'blocked' if any(w['severity']=='danger' for w in warnings) else ('warnings' if warnings else 'passed'),'summary':'Review complete with actionable checks.','warnings':warnings,'suggestions':suggestions}
    meta=(db.get(m.ContentVersion,d.current_version_id).metadata_json or {}) if d.current_version_id else {}; meta['compliance_result']=result; meta['warnings']=warnings; _save_version(d,db,u,meta,False); db.commit(); return {'draft':_draft_json(d,db),'compliance_result':result}
@app.post('/studio/drafts/{id}/send-for-approval')
def studio_send_approval(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d,_,brand=_assert_draft(id,u,db); acc=db.query(m.ChannelAccount).filter(m.ChannelAccount.brand_id==brand.id,m.ChannelAccount.provider.in_(['telegram','bale','email','approval_link'])).first()
    if not acc: _studio_error(422,'missing_approval_method','Connect an approval method before sending.',{'action_href':'/app/integrations'})
    tok=token_urlsafe(24); ar=m.ApprovalRequest(draft_id=id,requested_by_user_id=u.id,public_token_hash=sha256(tok.encode()).hexdigest()); db.add(ar); d.status='in_review'; db.commit(); return {'approval_request_id':ar.id,'status':ar.status,'approval_url':f'/public/approval/{tok}','draft':_draft_json(d,db)}
@app.post('/studio/drafts/{id}/schedule')
def studio_schedule(id:int,payload:StudioScheduleIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d,_,brand=_assert_draft(id,u,db); acc=db.query(m.ChannelAccount).filter_by(brand_id=brand.id,provider=payload.channel or d.channel).first() or db.query(m.ChannelAccount).filter_by(brand_id=brand.id).first()
    if not acc: acc=m.ChannelAccount(brand_id=brand.id,provider=payload.channel or d.channel,account_name='Assisted publishing',account_identifier='assisted',connection_status='needs_credentials'); db.add(acc); db.flush()
    sp=m.ScheduledPost(draft_id=id,channel_account_id=acc.id,scheduled_at=datetime.fromisoformat(f"{payload.date}T{payload.time}:00"),status='scheduled'); db.add(sp); d.status='scheduled'; db.commit(); return {'scheduled_post_id':sp.id,'status':sp.status,'warning':None if acc.connection_status=='connected' else 'Connect channel before publishing.','draft':_draft_json(d,db)}
@app.post('/studio/drafts/{id}/export-assisted-kit')
def studio_export(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d,_,_=_assert_draft(id,u,db); j=_draft_json(d,db); kit=f"# {j['title']}\n\nChannel: {j['channel']}\nContent type: {j['content_type']}\n\nHook: {j.get('hook','')}\n\n{j['body']}\n\nCTA: {j.get('cta','')}\nHashtags: {j.get('hashtags','')}\n\nCompliance warnings: {j.get('warnings',[])}\nAsset suggestions: Use approved brand visuals."
    return {'filename':f"smarbiz-draft-{id}-kit.md",'content':kit}
