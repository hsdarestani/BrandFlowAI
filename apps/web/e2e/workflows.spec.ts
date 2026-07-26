import {expect,test,type APIRequestContext} from '@playwright/test';

const API=process.env.E2E_API_URL||'http://127.0.0.1:8000';
const unique=(prefix:string)=>`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
const headers=(token:string)=>({Authorization:`Bearer ${token}`});

async function signup(request:APIRequestContext){
 const response=await request.post(`${API}/auth/signup`,{data:{name:'Workflow tester',organization_name:unique('Workflow org'),email:`${unique('workflow')}@example.com`,password:'StrongPass123!',preferred_language:'fa',locale:'fa'}});
 expect(response.ok(),await response.text()).toBeTruthy();
 return (await response.json()).access_token as string;
}

async function setup(request:APIRequestContext,token:string){
 const h=headers(token);
 const responses=await Promise.all([
  request.patch(`${API}/settings/brand-defaults`,{headers:h,data:{name:'برند گردش‌کار',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa'}}),
  request.patch(`${API}/brand-pulse`,{headers:h,data:{brand_name:'برند گردش‌کار',website_url:'https://example.com',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa',brand_summary:'پلتفرم مدیریت عملیات محتوا',target_audience:'مدیران کسب‌وکار',audience_pain_points:['بی‌نظمی'],desired_outcomes:['برنامه منظم'],tone_of_voice:'شفاف و حرفه‌ای',writing_style:'کوتاه',content_pillars:['آموزش'],value_propositions:['صرفه‌جویی در زمان'],forbidden_claims:['تضمینی'],channel_notes:['instagram'],approval_preferences:'public_link'}}),
 ]);
 for(const response of responses)expect(response.ok(),await response.text()).toBeTruthy();
 const product=await request.post(`${API}/brand-pulse/products`,{headers:h,data:{name:'خدمت تست گردش‌کار',type:'service',description:'مدیریت کامل محتوا',benefits:['سرعت'],audience:'مدیران',status:'active'}});
 expect(product.ok(),await product.text()).toBeTruthy();
 const connector=await request.post(`${API}/integrations/connections`,{headers:h,data:{provider:'approval_link',display_name:'لینک عمومی تأیید',config:{}}});
 expect([200,201,409]).toContain(connector.status());
}

test('campaign, studio, approval, insights, reports, and cleanup complete one real workflow',async({request})=>{
 const token=await signup(request);await setup(request,token);const h=headers(token);

 const campaignResponse=await request.post(`${API}/campaigns`,{headers:h,data:{name:unique('کمپین تست'),goal:'تولید لید',description:'گردش‌کار خودکار',offer:'مشاوره رایگان',target_audience:'مدیران',start_date:new Date().toISOString().slice(0,10),end_date:new Date(Date.now()+7*86400000).toISOString().slice(0,10),status:'draft',channels:['instagram'],content_pillars:['آموزش'],budget:100}});
 expect(campaignResponse.ok(),await campaignResponse.text()).toBeTruthy();
 const campaign=await campaignResponse.json();expect(campaign.id).toBeTruthy();
 const campaignRead=await request.get(`${API}/campaigns/${campaign.id}`,{headers:h});expect(campaignRead.ok(),await campaignRead.text()).toBeTruthy();
 const campaignUpdate=await request.patch(`${API}/campaigns/${campaign.id}`,{headers:h,data:{name:campaign.name,goal:'افزایش ثبت‌نام',description:campaign.description,offer:campaign.offer,target_audience:campaign.target_audience,start_date:campaign.start_date,end_date:campaign.end_date,status:'planned',channels:['instagram','telegram'],content_pillars:['آموزش'],budget:150}});expect(campaignUpdate.ok(),await campaignUpdate.text()).toBeTruthy();
 const plan=await request.post(`${API}/campaigns/${campaign.id}/generate-plan`,{headers:h,data:{}});expect(plan.status(),await plan.text()).toBeLessThan(500);

 const draftResponse=await request.post(`${API}/studio/drafts`,{headers:h,data:{title:'پیش‌نویس گردش‌کار',body:'این متن واقعی برای بررسی چرخه کامل محتوا ساخته شده است.',hook:'چطور محتوای منظم بسازیم؟',cta:'برای مشاوره پیام بدهید',hashtags:'#اسماربیز',goal:'تولید لید',channel:'instagram',language:'fa',content_type:'post',product_or_offer:'خدمت تست گردش‌کار',tone:'شفاف',prompt:'یک پست آموزشی کوتاه بنویس',status:'draft'}});
 expect(draftResponse.ok(),await draftResponse.text()).toBeTruthy();
 const draft=await draftResponse.json();expect(draft.id).toBeTruthy();
 const draftUpdate=await request.patch(`${API}/studio/drafts/${draft.id}`,{headers:h,data:{...draft,title:'پیش‌نویس ویرایش‌شده گردش‌کار'}});expect(draftUpdate.ok(),await draftUpdate.text()).toBeTruthy();
 const compliance=await request.post(`${API}/studio/drafts/${draft.id}/compliance-check`,{headers:h,data:{}});expect(compliance.ok(),await compliance.text()).toBeTruthy();

 const approvalResponse=await request.post(`${API}/approvals/requests`,{headers:h,data:{draft_id:Number(draft.id),reviewer_name:'بازبین تست',reviewer_email:null,reviewer_phone:null,message:'لطفاً بررسی شود',due_at:null,method:'public_link'}});
 expect(approvalResponse.ok(),await approvalResponse.text()).toBeTruthy();
 const approval=await approvalResponse.json();expect(approval.id).toBeTruthy();expect(approval.public_url).toBeTruthy();
 const tokenPart=String(approval.public_url).split('/').filter(Boolean).pop();expect(tokenPart).toBeTruthy();
 const publicRead=await request.get(`${API}/public/approval/${encodeURIComponent(tokenPart!)}`);expect(publicRead.ok(),await publicRead.text()).toBeTruthy();
 const decision=await request.post(`${API}/public/approval/${encodeURIComponent(tokenPart!)}/decision`,{data:{action:'approve',reviewer_name:'بازبین تست',comment:'تأیید شد',revision_prompt:null,save_to_memory:true}});expect(decision.ok(),await decision.text()).toBeTruthy();
 expect((await decision.json()).status).toBe('approved');
 const approvalRead=await request.get(`${API}/approvals/requests/${approval.id}`,{headers:h});expect(approvalRead.ok(),await approvalRead.text()).toBeTruthy();expect((await approvalRead.json()).status).toBe('approved');

 const metric=await request.post(`${API}/insights/manual-metric`,{headers:h,data:{metric_date:new Date().toISOString().slice(0,10),channel:'instagram',metric_name:'impressions',metric_value:120,notes:'متریک تست خودکار',source:'manual',content_id:String(draft.id),campaign_id:String(campaign.id)}});expect(metric.ok(),await metric.text()).toBeTruthy();
 const insights=await request.get(`${API}/insights/overview`,{headers:h});expect(insights.ok(),await insights.text()).toBeTruthy();expect(JSON.stringify(await insights.json())).toContain('impressions');

 const reportResponse=await request.post(`${API}/reports/generate-weekly`,{headers:h,data:{period_start:new Date(Date.now()-6*86400000).toISOString().slice(0,10),period_end:new Date().toISOString().slice(0,10),language:'fa',audience:'internal'}});expect(reportResponse.ok(),await reportResponse.text()).toBeTruthy();
 const report=await reportResponse.json();expect(report.id).toBeTruthy();
 const exportResponse=await request.post(`${API}/reports/${report.id}/export`,{headers:h,data:{format:'markdown'}});expect(exportResponse.ok(),await exportResponse.text()).toBeTruthy();expect((await exportResponse.json()).available).toBeTruthy();

 const archiveDraft=await request.delete(`${API}/studio/drafts/${draft.id}`,{headers:h});expect(archiveDraft.ok(),await archiveDraft.text()).toBeTruthy();
 const deleteReport=await request.delete(`${API}/reports/${report.id}`,{headers:h});expect(deleteReport.ok(),await deleteReport.text()).toBeTruthy();
 const deleteCampaign=await request.delete(`${API}/campaigns/${campaign.id}`,{headers:h});expect(deleteCampaign.ok(),await deleteCampaign.text()).toBeTruthy();
});
