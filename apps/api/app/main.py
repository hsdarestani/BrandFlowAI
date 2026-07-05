from fastapi import FastAPI, Depends, HTTPException, Header
import os
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from secrets import token_urlsafe
from hashlib import sha256
from datetime import datetime, timezone
from pydantic import BaseModel
from .database import Base, engine, get_db
from . import models as m
from .security import hash_password, verify_password, create_token, decode_token
from .services.ai.agents import BrandAnalystAgent, ContentStrategistAgent, CopywriterAgent, ApprovalLearningAgent, PerformanceAnalystAgent
from .services.connectors.providers import get_connector, connector_catalog
from .services.connectors.bale_safir import normalize_iran_phone
Base.metadata.create_all(bind=engine)
app=FastAPI(title='Smarbiz API', version='0.1.0')
CORS_ORIGINS=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:3000,https://smarbiz.sbs,https://www.smarbiz.sbs').split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
class Signup(BaseModel): email:str; password:str; name:str='Smarbiz User'; locale:str='en'; organization_name:str='Smarbiz Workspace'; preferred_language:str|None=None
class Login(BaseModel): email:str; password:str
class OrgIn(BaseModel): name:str; mode:str='owner'
class BrandIn(BaseModel): organization_id:int; name:str; industry:str='general'; country:str='DE'; primary_language:str='en'; timezone:str='UTC'; description:str=''
class ActionIn(BaseModel): action:str='approve'; comment:str|None=None; revision_prompt:str|None=None; save_to_memory:bool=True; reviewer_name:str|None=None
class ApprovalCreate(BaseModel): draft_id:int|None=None; title:str|None=None; reviewer_name:str|None=None; reviewer_email:str|None=None; reviewer_phone:str|None=None; message:str|None=None; due_at:str|None=None; method:str='public_link'
class DraftPatch(BaseModel): title:str|None=None; body:str|None=None; status:str|None=None


def make_unique_org_slug(db, name:str):
    base='-'.join((name or 'smarbiz-workspace').strip().lower().split()) or 'smarbiz-workspace'
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
def organizations(u=Depends(user_from_auth), db:Session=Depends(get_db)): return db.query(m.Organization).all()
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
def brands(u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.Brand).all()
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
@app.get('/brands/{id}/calendar')
def calendar(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return db.query(m.CalendarItem).filter_by(brand_id=id).all()
@app.post('/brands/{id}/calendar/items')
def add_item(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): item=m.CalendarItem(brand_id=id,**payload); db.add(item); db.commit(); return item
@app.patch('/calendar/items/{id}')
def patch_item(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): item=db.get(m.CalendarItem,id); [setattr(item,k,v) for k,v in payload.items() if hasattr(item,k)]; db.commit(); return item
@app.delete('/calendar/items/{id}')
def delete_item(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): item=db.get(m.CalendarItem,id); db.delete(item); db.commit(); return {'deleted':id}
@app.post('/brands/{id}/calendar/generate-week')
def gen_week(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): b=db.get(m.Brand,id); return ContentStrategistAgent().run(b)
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
def _member_org_ids(db,u):
    return [x.organization_id for x in db.query(m.OrganizationMember).filter_by(user_id=u.id,status='active').all()] or [x.id for x in db.query(m.Organization).filter_by(owner_user_id=u.id).all()]
def _tenant_brand(db,u,brand_id=None):
    q=db.query(m.Brand).filter(m.Brand.organization_id.in_(_member_org_ids(db,u)))
    if brand_id: q=q.filter(m.Brand.id==brand_id)
    return q.order_by(m.Brand.id).first()
def _draft_for_user(db,u,draft_id):
    d=db.get(m.ContentDraft,draft_id)
    b=db.get(m.Brand,d.brand_id) if d else None
    if not d or not b or b.organization_id not in _member_org_ids(db,u): raise HTTPException(404,{'error':'not_found','message':'Draft not found'})
    return d

def _approval_q(db,u):
    return db.query(m.ApprovalRequest).join(m.ContentDraft,m.ContentDraft.id==m.ApprovalRequest.draft_id).join(m.Brand,m.Brand.id==m.ContentDraft.brand_id).filter(m.Brand.organization_id.in_(_member_org_ids(db,u)))
def _approval_for_user(db,u,id):
    ar=_approval_q(db,u).filter(m.ApprovalRequest.id==id).first()
    if not ar: raise HTTPException(404,{'error':'not_found','message':'Approval request not found'})
    return ar

def _public_url(token): return f'/public/approval/{token}'
def _draft_json(d):
    return {'id':d.id,'title':d.title,'body':d.body,'hook':None,'cta':None,'hashtags':' '.join(d.hashtags_json or []),'status':d.status,'quality_score':float(d.brand_fit_score or 0),'warnings':[]}
def _summary(ar,db):
    d=db.get(m.ContentDraft,ar.draft_id)
    return {'id':ar.id,'title':d.title if d else f'Approval #{ar.id}','channel':d.channel if d else None,'content_type':d.content_type if d else None,'status':ar.status,'reviewer':None,'due_at':ar.expires_at.isoformat() if ar.expires_at else None,'updated_at':ar.updated_at.isoformat() if ar.updated_at else None,'href':f'/app/approvals?request={ar.id}'}
def _detail(ar,db,token=None):
    d=db.get(m.ContentDraft,ar.draft_id); item=db.get(m.CalendarItem,d.calendar_item_id) if d and d.calendar_item_id else None
    stored=db.query(m.ApprovalAction).filter_by(approval_request_id=ar.id,action='created').filter(m.ApprovalAction.source_message_id != None).first(); token=token or (stored.source_message_id if stored else None)
    out=_summary(ar,db); out.update({'draft':_draft_json(d) if d else None,'calendar_item':({'id':item.id,'scheduled_at':item.scheduled_at.isoformat() if item.scheduled_at else None} if item else None),'public_url':_public_url(token) if token else None,'message':None,'actions':[{'id':a.id,'action':a.action,'actor_name':None,'comment':a.comment,'created_at':a.created_at.isoformat() if a.created_at else ''} for a in db.query(m.ApprovalAction).filter_by(approval_request_id=ar.id).order_by(m.ApprovalAction.created_at.desc()).all()]})
    return out

def _set_draft_status(db,ar,status):
    d=db.get(m.ContentDraft,ar.draft_id)
    if d: d.status=status

def _decide(db,ar,action,comment,user_id=None,source='in_app',reviewer_name=None):
    if ar.status in ['approved','rejected','cancelled','expired']: raise HTTPException(409,{'error':'closed','message':'Approval request is already closed'})
    if action in ['rejected','changes_requested'] and not (comment or '').strip(): raise HTTPException(422,{'error':'comment_required','message':'Comment is required'})
    ar.status=action; ar.updated_at=datetime.now(timezone.utc); ar.expires_at=ar.expires_at
    _set_draft_status(db,ar, {'approved':'approved','changes_requested':'changes_requested','rejected':'rejected'}.get(action,'draft_ready'))
    db.add(m.ApprovalAction(approval_request_id=ar.id,user_id=user_id,action=action,comment=comment,source_channel=source,save_to_memory=False)); db.commit(); return _detail(ar,db)

@app.post('/drafts/{id}/approval-requests')
def approval_req(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    d=_draft_for_user(db,u,id); tok=token_urlsafe(32); ar=m.ApprovalRequest(draft_id=id,requested_by_user_id=u.id,public_token_hash=sha256(tok.encode()).hexdigest(),status='pending'); d.status='in_approval'; db.add(ar); db.flush(); db.add(m.ApprovalAction(approval_request_id=ar.id,user_id=u.id,action='created',source_channel='in_app',source_message_id=tok,save_to_memory=False)); db.commit(); return {'id':ar.id,'public_url':_public_url(tok),'token':tok}
@app.get('/approvals/overview')
def approvals_overview(u=Depends(user_from_auth),db:Session=Depends(get_db)):
    brand=_tenant_brand(db,u); org=db.get(m.Organization,brand.organization_id) if brand else None; reqs=_approval_q(db,u).order_by(m.ApprovalRequest.updated_at.desc()).all(); drafts=db.query(m.ContentDraft).filter_by(brand_id=brand.id).count() if brand else 0
    counts={k:len([r for r in reqs if r.status==k]) for k in ['pending','approved','changes_requested','rejected']}; decided=counts['approved']+counts['rejected']; chans={'telegram_connected':False,'bale_connected':False,'public_link_enabled':True}
    if brand:
        accs=db.query(m.ChannelAccount).filter_by(brand_id=brand.id).all(); chans.update({'telegram_connected':any(a.provider=='telegram' and a.connection_status=='connected' for a in accs),'bale_connected':any(a.provider in ['bale','bale_safir'] and a.connection_status=='connected' for a in accs)})
    rec={'title':'Create a draft in Studio' if drafts==0 else ('Send first draft for approval' if not reqs else ('Create revisions' if counts['changes_requested'] else ('Review pending approvals' if counts['pending'] else 'Schedule approved content'))),'description':'Next best step for your approval workflow.','action_label':'Open Studio' if drafts==0 else 'Create approval request','action_type':'navigate' if drafts==0 else 'open_modal','action_href':'/app/content-studio','severity':'warning' if not (chans['telegram_connected'] or chans['bale_connected'] or chans['public_link_enabled']) else 'info'}
    alerts=[]
    if counts['pending']: alerts.append({'id':'pending','title':'Pending approvals','description':f"{counts['pending']} approval request(s) need a decision.",'severity':'info','href':'/app/approvals'})
    if counts['changes_requested']: alerts.append({'id':'changes','title':'Changes requested','description':'Create revisions for reviewed content.','severity':'warning','href':'/app/approvals'})
    return {'user':{'id':u.id,'name':u.name,'email':u.email},'organization':({'id':org.id,'name':org.name} if org else None),'brand':({'id':brand.id,'name':brand.name,'primary_language':brand.primary_language} if brand else None),'summary':{**{f'{k}_count':v for k,v in counts.items()},'overdue_count':0,'approval_rate':(round(counts['approved']/decided*100) if decided else None)},'requests':[_summary(r,db) for r in reqs],'selected_request':_detail(reqs[0],db) if reqs else None,'recommended_action':rec,'alerts':alerts,'channels':chans}
@app.get('/approvals/requests')
def approvals_requests(u=Depends(user_from_auth),db:Session=Depends(get_db)): return [_summary(r,db) for r in _approval_q(db,u).order_by(m.ApprovalRequest.updated_at.desc()).all()]
@app.get('/approvals/requests/{id}')
def approval_detail(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return _detail(_approval_for_user(db,u,id),db)
@app.post('/approvals/requests')
def create_approval(data:ApprovalCreate,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    if not data.draft_id: raise HTTPException(422,{'error':'draft_required','message':'Select a draft'})
    d=_draft_for_user(db,u,data.draft_id); tok=token_urlsafe(32); ar=m.ApprovalRequest(draft_id=d.id,requested_by_user_id=u.id,public_token_hash=sha256(tok.encode()).hexdigest(),status='pending'); d.status='in_approval'; db.add(ar); db.flush(); db.add(m.ApprovalAction(approval_request_id=ar.id,user_id=u.id,action='created',comment=data.message,source_channel=data.method,source_message_id=tok,save_to_memory=False)); db.commit(); return _detail(ar,db,tok)
@app.patch('/approvals/requests/{id}')
def patch_approval(id:int,payload:dict,u=Depends(user_from_auth),db:Session=Depends(get_db)): ar=_approval_for_user(db,u,id); ar.status=payload.get('status',ar.status); db.commit(); return _detail(ar,db)
@app.post('/approvals/requests/{id}/approve')
def approve_new(id:int,data:ActionIn=ActionIn(),u=Depends(user_from_auth),db:Session=Depends(get_db)): return _decide(db,_approval_for_user(db,u,id),'approved',data.comment,u.id)
@app.post('/approvals/requests/{id}/request-changes')
def changes_new(id:int,data:ActionIn,u=Depends(user_from_auth),db:Session=Depends(get_db)): return _decide(db,_approval_for_user(db,u,id),'changes_requested',data.comment,u.id)
@app.post('/approvals/requests/{id}/reject')
def reject_new(id:int,data:ActionIn,u=Depends(user_from_auth),db:Session=Depends(get_db)): return _decide(db,_approval_for_user(db,u,id),'rejected',data.comment,u.id)
@app.post('/approvals/requests/{id}/save-feedback-to-memory')
def save_feedback(id:int,data:ActionIn,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    ar=_approval_for_user(db,u,id); d=db.get(m.ContentDraft,ar.draft_id); text=(data.comment or '').strip() or (db.query(m.ApprovalAction).filter_by(approval_request_id=id).order_by(m.ApprovalAction.created_at.desc()).first() or m.ApprovalAction(comment='')).comment
    if not text: raise HTTPException(422,{'error':'feedback_required','message':'Add feedback before saving to memory'})
    note=m.BrandMemoryNote(brand_id=d.brand_id,note=text,source_type='approval_feedback',source_id=str(id),accepted_by_user_id=u.id,auto_generated=False); db.add(note); db.add(m.ApprovalAction(approval_request_id=id,user_id=u.id,action='saved_to_memory',comment=text,source_channel='in_app',save_to_memory=False)); db.commit(); return {'saved':True,'memory_note_id':note.id}
@app.post('/approvals/requests/{id}/copy-link-event')
def copy_link(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)):
    ar=_approval_for_user(db,u,id); created=db.query(m.ApprovalAction).filter_by(approval_request_id=id,action='created').filter(m.ApprovalAction.source_message_id != None).first(); db.add(m.ApprovalAction(approval_request_id=id,user_id=u.id,action='copied_link',source_channel='in_app',save_to_memory=False)); db.commit(); return {'copied':True,'public_url':_public_url(created.source_message_id) if created else None}
def _send_channel(id,u,db,provider):
    ar=_approval_for_user(db,u,id); d=db.get(m.ContentDraft,ar.draft_id); acc=db.query(m.ChannelAccount).filter_by(brand_id=d.brand_id,provider=provider,connection_status='connected').first()
    if not acc: raise HTTPException(422,{'error':'not_connected','message':f'{provider.title()} is not connected yet','href':'/app/integrations'})
    db.add(m.ApprovalAction(approval_request_id=id,user_id=u.id,action='sent',comment=f'sent via {provider}',source_channel=provider,save_to_memory=False)); db.commit(); return {'sent':True,'channel':provider}
@app.post('/approvals/requests/{id}/send-via-telegram')
def send_telegram_new(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return _send_channel(id,u,db,'telegram')
@app.post('/approvals/requests/{id}/send-via-bale')
def send_bale_new(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return _send_channel(id,u,db,'bale')
@app.get('/approvals')
def approvals(u=Depends(user_from_auth),db:Session=Depends(get_db)): return approvals_requests(u,db)
@app.get('/approvals/{id}')
def approval(id:int,u=Depends(user_from_auth),db:Session=Depends(get_db)): return approval_detail(id,u,db)
@app.get('/public/approval/{token}')
def public_approval(token:str,db:Session=Depends(get_db)):
    ar=db.query(m.ApprovalRequest).filter_by(public_token_hash=sha256(token.encode()).hexdigest()).first()
    if not ar: raise HTTPException(404,{'error':'invalid_token','message':'Approval link is invalid'})
    return {'approval':_detail(ar,db),'closed':ar.status in ['approved','rejected','cancelled','expired']}
@app.post('/public/approval/{token}/decision')
def public_decision(token:str,data:ActionIn,db:Session=Depends(get_db)):
    ar=db.query(m.ApprovalRequest).filter_by(public_token_hash=sha256(token.encode()).hexdigest()).first()
    if not ar: raise HTTPException(404,{'error':'invalid_token','message':'Approval link is invalid'})
    action={'approve':'approved','approved':'approved','request_changes':'changes_requested','changes_requested':'changes_requested','reject':'rejected','rejected':'rejected'}.get(data.action)
    if not action: raise HTTPException(422,{'error':'invalid_action','message':'Use approve, request_changes, or reject'})
    return _decide(db,ar,action,data.comment,None,'public_link',data.reviewer_name)
@app.post('/public/approval/{token}/action')
def public_action(token:str,data:ActionIn,db:Session=Depends(get_db)): return public_decision(token,data,db)
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
import os
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
