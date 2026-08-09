import {expect,test,type APIRequestContext,type Page} from '@playwright/test';

const API_URL=process.env.E2E_API_URL||'http://127.0.0.1:8000';
const unique=(prefix:string)=>`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;
const headers=(token:string)=>({Authorization:`Bearer ${token}`});

async function createMobileWorkspace(request:APIRequestContext){
 const email=`${unique('mobile')}@example.com`;
 const signup=await request.post(`${API_URL}/auth/signup`,{data:{name:'کاربر موبایل',organization_name:`سازمان ${unique('mobile')}`,email,password:'StrongPass123!',preferred_language:'fa',locale:'fa'}});
 expect(signup.ok(),await signup.text()).toBeTruthy();
 const token=(await signup.json()).access_token as string;
 const h=headers(token);
 const setup=await Promise.all([
  request.patch(`${API_URL}/settings/organization`,{headers:h,data:{name:'سازمان تست موبایل',mode:'owner'}}),
  request.patch(`${API_URL}/settings/brand-defaults`,{headers:h,data:{name:'برند تست موبایل',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa'}}),
  request.patch(`${API_URL}/settings/profile`,{headers:h,data:{locale:'fa',timezone:'Asia/Tehran'}}),
  request.patch(`${API_URL}/brand-pulse`,{headers:h,data:{brand_name:'برند تست موبایل',website_url:'https://example.com',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa',brand_summary:'ابزار مدیریت عملیات محتوای کسب‌وکارها',target_audience:'مدیران کسب‌وکارهای کوچک',audience_pain_points:['بی‌نظمی محتوا'],desired_outcomes:['برنامه منظم'],tone_of_voice:'شفاف و حرفه‌ای',writing_style:'کوتاه و مشخص',content_pillars:['آموزش','اعتماد'],value_propositions:['صرفه‌جویی در زمان'],forbidden_claims:['نتیجه تضمینی'],channel_notes:['instagram'],approval_preferences:'public_link'}})
 ]);
 for(const response of setup)expect(response.ok(),await response.text()).toBeTruthy();
 const product=await request.post(`${API_URL}/brand-pulse/products`,{headers:h,data:{name:'خدمت موبایل',type:'service',description:'خدمت تست رابط موبایل',benefits:['سرعت'],audience:'مدیران',status:'active'}});
 expect(product.ok(),await product.text()).toBeTruthy();
 const connector=await request.post(`${API_URL}/integrations/connections`,{headers:h,data:{provider:'approval_link',display_name:'لینک عمومی تأیید',config:{}}});
 expect([200,201,409]).toContain(connector.status());
 return token;
}

async function installSession(page:Page,token:string){
 await page.addInitScript(value=>{
  localStorage.setItem('smarbiz_token',value);
  localStorage.setItem('smarbiz_locale','fa');
 },token);
}

async function expectNoPageOverflow(page:Page,route:string){
 const result=await page.evaluate(()=>{
  const width=window.innerWidth;
  const scrollWidth=Math.max(document.documentElement.scrollWidth,document.body.scrollWidth);
  const offenders=[...document.querySelectorAll<HTMLElement>('body *')].filter(element=>{
   const style=getComputedStyle(element);
   if(style.display==='none'||style.visibility==='hidden'||Number(style.opacity)===0)return false;
   const rect=element.getBoundingClientRect();
   if(rect.width===0&&rect.height===0)return false;
   if(element.closest('.table,.pipeline,.overflow-x-auto'))return false;
   return rect.left<-2||rect.right>width+2;
  }).slice(0,8).map(element=>({tag:element.tagName,className:String(element.className).slice(0,140),rect:element.getBoundingClientRect().toJSON()}));
  return {width,scrollWidth,offenders};
 });
 expect(result.scrollWidth,`${route}: document width ${result.scrollWidth} > viewport ${result.width}`).toBeLessThanOrEqual(result.width+1);
 expect(result.offenders,`${route}: elements outside viewport ${JSON.stringify(result.offenders)}`).toEqual([]);
}

async function expectTouchTargets(page:Page){
 const targets=await page.locator('.mobile-bottom-nav a,.mobile-bottom-nav button,.mobile-header-button').evaluateAll(elements=>elements.filter(element=>getComputedStyle(element).display!=='none').map(element=>{const rect=element.getBoundingClientRect();return {label:element.getAttribute('aria-label')||element.textContent?.trim(),width:rect.width,height:rect.height}}));
 expect(targets.length).toBeGreaterThanOrEqual(7);
 for(const target of targets){expect(target.width,`${target.label} touch width`).toBeGreaterThanOrEqual(40);expect(target.height,`${target.label} touch height`).toBeGreaterThanOrEqual(40)}
}

const modules=['dashboard','calendar','content-studio','approvals','campaigns','analytics','reports','brand-pulse','assets','integrations','settings','help'];
const viewports=[
 {name:'small Android',width:320,height:740},
 {name:'iPhone standard',width:375,height:812},
 {name:'modern Android',width:390,height:844},
 {name:'large phone',width:430,height:932}
];

for(const viewport of viewports){
 test(`all application modules fit ${viewport.name} (${viewport.width}px)`,async({page,request})=>{
  const token=await createMobileWorkspace(request);
  await installSession(page,token);
  await page.setViewportSize({width:viewport.width,height:viewport.height});
  for(const module of modules){
   await page.goto(`/fa/app/${module}`,{waitUntil:'domcontentloaded'});
   await expect(page.locator('.mobile-app-header')).toBeVisible();
   await expect(page.locator('.mobile-bottom-nav')).toBeVisible();
   await expect(page.locator('.desktop-app-sidebar')).toBeHidden();
   await expect(page.locator('main.app-content')).toBeVisible();
   await expect(page.locator('body')).not.toContainText(/Application error|Internal Server Error|خطای داخلی سرور/i);
   await expectNoPageOverflow(page,module);
   await expectTouchTargets(page);
  }
  await page.getByRole('button',{name:'بیشتر'}).click();
  await expect(page.getByRole('dialog',{name:'بخش‌های بیشتر'})).toBeVisible();
  await expect(page.getByRole('dialog',{name:'بخش‌های بیشتر'}).getByText('کمپین‌ها',{exact:true})).toBeVisible();
  await expectNoPageOverflow(page,'more sheet');
 });
}

test('auth and onboarding chat stay usable on a 320px phone and landscape phone',async({page,request})=>{
 for(const size of [{width:320,height:740},{width:844,height:390}]){
  await page.setViewportSize(size);
  await page.goto('/fa/auth/login');
  await expect(page.getByRole('heading',{name:'خوش برگشتی'})).toBeVisible();
  await expectNoPageOverflow(page,`login ${size.width}x${size.height}`);
  await page.goto('/fa/auth/signup');
  await expect(page.getByRole('heading',{name:'فضای کاری اسماربیز را بساز'})).toBeVisible();
  await expectNoPageOverflow(page,`signup ${size.width}x${size.height}`);
 }
 const token=await createMobileWorkspace(request);
 await installSession(page,token);
 await page.setViewportSize({width:320,height:740});
 await page.goto('/fa/onboarding');
 await expect(page.getByRole('heading',{name:'اسماربیز را برای کسب‌وکار خودت می‌خواهی یا برای مشتری‌ها؟'})).toBeVisible();
 await expect(page.getByText('سؤال 1 از 10',{exact:true})).toBeVisible();
 await expectNoPageOverflow(page,'onboarding chat 320px');
 const buttons=await page.getByRole('button').evaluateAll(elements=>elements.filter(element=>getComputedStyle(element).display!=='none').map(element=>element.getBoundingClientRect().height));
 expect(Math.min(...buttons)).toBeGreaterThanOrEqual(38);
});
