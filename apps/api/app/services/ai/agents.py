from datetime import datetime, timedelta, timezone
from .providers import get_ai_provider
class BrandAnalystAgent:
    def __init__(self): self.ai=get_ai_provider()
    def run(self, onboarding):
        lang=onboarding.get('primary_language','en')
        return {'voice':{'tone':onboarding.get('tone','friendly'),'sales_intensity':'medium','language':lang},'visual':{'style':'premium SaaS-ready'},'compliance':{'regulated':onboarding.get('regulated',False),'required_disclaimers':onboarding.get('required_disclaimers',[])},'channel_rules':{'instagram':'story-first','telegram':'price-and-cta-earlier','bale':'Persian-first direct CTA'},'cta_library':['Book a call','Order now','Request approval'],'forbidden_words':['guaranteed cure','risk-free profit']}
class ContentStrategistAgent:
    def run(self, brand, goals=None):
        now=datetime.now(timezone.utc)
        pillars=[{'name':'Education','description':'Helpful authority content','weight':1.0},{'name':'Proof','description':'Trust and testimonials','weight':.8},{'name':'Offer','description':'Conversion content','weight':.7}]
        calendar=[{'title':f'{p["name"]} post {i+1}','description':p['description'],'scheduled_at':(now+timedelta(days=i)).isoformat(),'channels':['instagram','telegram','bale'] if brand.primary_language=='fa' else ['instagram','linkedin','google_business'],'content_type':'post','goal':(goals or ['awareness'])[0]} for i,p in enumerate((pillars*3)[:7])]
        return {'pillars':pillars,'calendar':calendar}
class CopywriterAgent:
    def run(self,item,brand_dna,channel='instagram',language='en'):
        body={'fa':'این پست با لحن گرم برند شما نوشته شده است. برای سفارش پیام بدهید.','de':'Sachlicher, regelkonformer Beitrag mit klarem Nutzen und vorsichtigem Leistungsversprechen.','en':'A clear, benefit-led post that matches your brand voice and invites the next step.'}.get(language)
        return {'title':item.title,'body':body,'hashtags':['#BrandFlowAI','#ContentOps',f'#{channel}'],'brand_fit_score':.88,'compliance_score':.91}
class ComplianceReviewerAgent:
    def run(self,draft,industry='general',language='en',rules=None): return {'risk_score':.12,'warnings':['Avoid guaranteed outcomes'] if industry in ['medical','finance','legal','beauty'] else [],'safer_rewrite':draft.body}
class ApprovalLearningAgent:
    def run(self,action): return {'note':f"Client action '{action.action}' suggests future copy should reflect: {action.comment or action.revision_prompt or 'approved direction'}",'confidence_score':.78}
class PerformanceAnalystAgent:
    def run(self,metrics): return {'what_worked':'Posts with explicit CTA won','best_channel':'bale' if metrics.get('orders',0)>0 else 'instagram','recommendations':['Shift one more conversion post to Telegram/Bale','Keep German regulated claims conservative']}
class CampaignBuilderAgent:
    def run(self,product,offer,goal): return {'strategy':f'{goal} campaign for {product.name}','content_package':['awareness post','proof post','conversion post'],'tracking':{'utm_campaign':product.name.lower().replace(' ','-')}}
