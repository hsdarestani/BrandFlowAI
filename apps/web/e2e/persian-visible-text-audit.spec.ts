import {expect,test,type APIRequestContext,type Page} from '@playwright/test';

const API_URL=process.env.E2E_API_URL||'http://127.0.0.1:8000';
const unique=(prefix:string)=>`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
const modules=['dashboard','calendar','content-studio','approvals','campaigns','analytics','reports','brand-pulse','assets','integrations','settings','help'];

async function createPersianSession(request:APIRequestContext,seeded:boolean){
 const email=`${unique(seeded?'audit-seeded':'audit-empty')}@example.com`;
 const signup=await request.post(`${API_URL}/auth/signup`,{data:{name:'کاربر ممیزی فارسی',organization_name:'سازمان ممیزی فارسی',email,password:'StrongPass123!',preferred_language:'fa',locale:'fa'}});
 expect(signup.ok(),await signup.text()).toBeTruthy();
 const token=(await signup.json()).access_token as string;
 if(seeded){
  const headers={Authorization:`Bearer ${token}`};
  const calls=[
   request.patch(`${API_URL}/settings/organization`,{headers,data:{name:'سازمان ممیزی فارسی',mode:'owner'}}),
   request.patch(`${API_URL}/settings/brand-defaults`,{headers,data:{name:'برند ممیزی فارسی',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa'}}),
   request.patch(`${API_URL}/settings/profile`,{headers,data:{locale:'fa',timezone:'Asia/Tehran'}}),
   request.patch(`${API_URL}/brand-pulse`,{headers,data:{brand_name:'برند ممیزی فارسی',website_url:'https://example.com',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa',brand_summary:'سامانه مدیریت عملیات محتوا',target_audience:'مدیران کسب‌وکار',audience_pain_points:['بی‌نظمی محتوا'],desired_outcomes:['برنامه منظم'],tone_of_voice:'شفاف و حرفه‌ای',writing_style:'کوتاه و مشخص',content_pillars:['آموزش','اعتماد'],value_propositions:['صرفه‌جویی در زمان'],forbidden_claims:['نتیجه تضمینی'],channel_notes:['اینستاگرام'],approval_preferences:'لینک عمومی'}}),
  ];
  for(const response of await Promise.all(calls))expect(response.ok(),await response.text()).toBeTruthy();
  const product=await request.post(`${API_URL}/brand-pulse/products`,{headers,data:{name:'خدمت مدیریت محتوا',type:'service',description:'خدمت واقعی ممیزی',benefits:['سرعت'],audience:'مدیران',status:'active'}});
  expect(product.ok(),await product.text()).toBeTruthy();
  const connector=await request.post(`${API_URL}/integrations/connections`,{headers,data:{provider:'approval_link',display_name:'لینک عمومی تأیید',config:{}}});
  expect([200,201,409]).toContain(connector.status());
 }
 return token;
}

async function installSession(page:Page,token:string){
 await page.addInitScript(value=>{
  localStorage.setItem('smarbiz_token',value);
  localStorage.setItem('smarbiz_locale','fa');
 },token);
}

const properNames=/\b(?:Smarbiz|Instagram|Telegram|Bale(?:\s+Safir|\s+Bot)?|LinkedIn|Google(?:\s+Business|\s+Analytics)?|YouTube(?:\s+Analytics)?|TikTok|WooCommerce|Mailchimp|Brevo|Eitaa|Soroush|Aparat|Rubika|Meta(?:\s+Insights)?|GA4|API|AI|JSON|URL|UTM|UTC|Asia\/Tehran|IR|DE)\b/gi;
const suspiciousSingle=/^(?:Compliance|Cancel|Save|Edit|Delete|Archive|Retry|Search|Status|Name|Type|Description|Audience|Benefits|Language|Channel|Price|Warning|Draft|Active|Archived|Completion|Workspace|Loading|Settings|Help|Reports|Campaigns|Insights|Assets|Integrations|Product|Service|Persona|Memory|Rules|Preview|Brief|Goal|Tone|Prompt|Title|Body|Hook|Hashtags|Translate|Rewrite|Shorten|Scheduled|Published|Pending|Approved)(?:\b|\s|:)/i;

function englishOffenders(text:string){
 const uniqueLines=new Set<string>();
 for(const rawLine of text.split('\n')){
  const line=rawLine.replace(/https?:\/\/\S+|\b\S+@\S+\b/g,'').replace(properNames,'').replace(/\s+/g,' ').trim();
  if(!line)continue;
  const words=line.match(/\b[A-Za-z][A-Za-z/-]{2,}\b/g)||[];
  if(words.length>=2||suspiciousSingle.test(line))uniqueLines.add(rawLine.trim());
 }
 return [...uniqueLines].filter(Boolean).slice(0,30);
}

for(const seeded of [false,true]){
 test(`all Persian modules avoid visible English copy (${seeded?'configured':'new'} workspace)`,async({page,request})=>{
  const token=await createPersianSession(request,seeded);
  await installSession(page,token);
  const report:Record<string,string[]>={};
  for(const module of modules){
   await page.goto(`/fa/app/${module}`,{waitUntil:'domcontentloaded'});
   await expect(page.locator('main.app-content')).toBeVisible();
   const offenders=englishOffenders(await page.locator('main.app-content').innerText());
   if(offenders.length)report[module]=offenders;
  }
  expect(report,`Visible English copy remains in Persian modules:\n${JSON.stringify(report,null,2)}`).toEqual({});
 });
}
