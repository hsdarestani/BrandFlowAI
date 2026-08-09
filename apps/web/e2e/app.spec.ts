import {expect,test,type APIRequestContext,type Page} from '@playwright/test';

const API_URL=process.env.E2E_API_URL||'http://127.0.0.1:8000';
const unique=(prefix:string)=>`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;

type Session={token:string;email:string};

async function createSession(request:APIRequestContext,locale='fa'):Promise<Session>{
 const email=`${unique('e2e')}@example.com`;
 const response=await request.post(`${API_URL}/auth/signup`,{data:{name:'کاربر تست',organization_name:`سازمان ${unique('test')}`,email,password:'StrongPass123!',preferred_language:locale,locale}});
 expect(response.ok(),await response.text()).toBeTruthy();
 const payload=await response.json();
 expect(payload.access_token).toBeTruthy();
 return {token:payload.access_token,email};
}

const authHeaders=(token:string)=>({Authorization:`Bearer ${token}`});

async function seedWorkspace(request:APIRequestContext,token:string){
 const headers=authHeaders(token);
 const calls=[
  request.patch(`${API_URL}/settings/organization`,{headers,data:{name:'فضای تست خودکار',mode:'owner'}}),
  request.patch(`${API_URL}/settings/brand-defaults`,{headers,data:{name:'برند تست خودکار',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa'}}),
  request.patch(`${API_URL}/settings/profile`,{headers,data:{locale:'fa',timezone:'Asia/Tehran'}}),
  request.patch(`${API_URL}/brand-pulse`,{headers,data:{brand_name:'برند تست خودکار',website_url:'https://example.com',industry:'نرم‌افزار',country:'IR',timezone:'Asia/Tehran',primary_language:'fa',brand_summary:'ابزار مدیریت عملیات محتوای کسب‌وکارها',target_audience:'مدیران کسب‌وکارهای کوچک',audience_pain_points:['بی‌نظمی محتوا'],desired_outcomes:['برنامه منظم'],tone_of_voice:'شفاف و حرفه‌ای',writing_style:'کوتاه و مشخص',content_pillars:['آموزش','اعتماد'],value_propositions:['صرفه‌جویی در زمان'],forbidden_claims:['نتیجه تضمینی'],channel_notes:['instagram'],approval_preferences:'public_link'}}),
 ];
 const responses=await Promise.all(calls);
 for(const response of responses)expect(response.ok(),await response.text()).toBeTruthy();
 const product=await request.post(`${API_URL}/brand-pulse/products`,{headers,data:{name:`محصول ${unique('e2e')}`,type:'service',description:'خدمت تست خودکار',benefits:['سریع'],audience:'مدیران',status:'active'}});
 expect(product.ok(),await product.text()).toBeTruthy();
 const connector=await request.post(`${API_URL}/integrations/connections`,{headers,data:{provider:'approval_link',display_name:'لینک عمومی تأیید',config:{}}});
 expect([200,201,409]).toContain(connector.status());
 const activate=await request.post(`${API_URL}/onboarding/activate`,{headers,data:{}});
 expect(activate.ok(),await activate.text()).toBeTruthy();
 // Generic browser/tenant tests intentionally do not invoke the external AI
 // endpoint. Real AI behavior is covered by backend provider/planner tests and
 // the production deployment smoke test with a real secret.
}

async function installSession(page:Page,token:string){
 await page.addInitScript(value=>{
  localStorage.setItem('smarbiz_token',value);
  localStorage.setItem('smarbiz_locale','fa');
 },token);
}

function captureRuntimeErrors(page:Page){
 const errors:string[]=[];
 page.on('pageerror',error=>errors.push(`pageerror: ${error.message}`));
 page.on('console',message=>{
  if(message.type()==='error'&&!message.text().includes('favicon'))errors.push(`console: ${message.text()}`);
 });
 return errors;
}

test('root locale, Persian direction, font, and auth copy are correct',async({page,context})=>{
 await context.addCookies([{name:'smarbiz_locale',value:'de',domain:'127.0.0.1',path:'/'}]);
 await page.goto('/');
 await expect(page).toHaveURL(/\/de\/?$/);
 await page.goto('/fa/auth/signup');
 await expect(page.locator('html')).toHaveAttribute('lang','fa');
 await expect(page.locator('html')).toHaveAttribute('dir','rtl');
 await expect(page.getByRole('heading',{name:'فضای کاری اسماربیز را بساز'})).toBeVisible();
 const font=await page.locator('body').evaluate(element=>getComputedStyle(element).fontFamily);
 expect(font.toLowerCase()).toContain('vazirmatn');
 const signupText=await page.locator('body').innerText();
 for(const stale of ['Workspace onboarding','Your first usable result','First week'])expect(signupText).not.toContain(stale);
 await page.goto('/fa/auth/login');
 await expect(page.getByRole('heading',{name:'خوش برگشتی'})).toBeVisible();
 const loginText=await page.locator('body').innerText();
 for(const stale of ['Brand-aware','Approval-ready','Measured'])expect(loginText).not.toContain(stale);
 await page.getByRole('button',{name:'English'}).click();
 await expect(page).toHaveURL(/\/en\/auth\/login/);
 await expect(page.getByRole('heading',{name:'Welcome back'})).toBeVisible();
});

test('a new Persian user can register, complete the ten-question chat, and reach guided activation',async({page})=>{
 const runtimeErrors=captureRuntimeErrors(page);
 const email=`${unique('browser')}@example.com`;
 await page.goto('/fa/auth/signup');
 await page.getByLabel('نام شما').fill('کاربر مرورگر');
 await page.getByLabel('سازمان / برند').fill('سازمان مرورگر');
 await page.getByLabel('ایمیل کاری').fill(email);
 await page.getByLabel('رمز عبور',{exact:true}).fill('StrongPass123!');
 await page.getByLabel('تکرار رمز عبور').fill('StrongPass123!');
 await page.getByRole('checkbox').check();
 await page.getByRole('button',{name:'ساخت فضای کاری'}).click();
 await expect(page).toHaveURL(/\/fa\/onboarding/);
 await expect(page.getByRole('heading',{name:'اسماربیز را برای کسب‌وکار خودت می‌خواهی یا برای مشتری‌ها؟'})).toBeVisible();
 await expect(page.getByText('سؤال 1 از 10',{exact:true})).toBeVisible();

 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/نام برند/).fill('برند مرورگر');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/حوزه فعالیت/).fill('نرم‌افزار');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/توضیح کسب‌وکار/).fill('یک ابزار برای مدیریت عملیات محتوا');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/مخاطب هدف/).fill('مدیران کسب‌وکارهای کوچک');
 await page.getByLabel(/دردها \/ سؤال‌های اصلی/).fill('بی‌نظمی در تولید محتوا');
 await page.getByLabel(/نتیجه‌ای که می‌خواهد/).fill('برنامه منظم و قابل اجرا');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/محصول \/ خدمت اصلی/).fill('مدیریت محتوای ماهانه');
 await page.getByLabel(/پیشنهاد شامل چیست/).fill('برنامه‌ریزی، تولید و تأیید محتوای ماهانه');
 await page.getByLabel(/مزیت‌ها و ارزش‌های کلیدی/).fill('سرعت\nکیفیت یکدست');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/لحن برند/).fill('شفاف، آرام و حرفه‌ای');
 await page.getByLabel(/سبک نوشتن/).fill('جمله‌های کوتاه و مشخص');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/ستون‌های محتوا/).fill('آموزش\nاعتمادسازی');
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await expect(page.getByText('اینستاگرام',{exact:true})).toBeVisible();
 await expect(page.getByText('لینک عمومی تأیید',{exact:true})).toBeVisible();
 await page.getByRole('button',{name:'ذخیره و ادامه'}).click();
 await page.getByLabel(/ادعاها \/ عبارت‌های ممنوع/).fill('نتیجه تضمینی');
 await expect(page.getByText('تمام شد؛ فقط همین ۱۰ سؤال بود.')).toBeVisible();
 // The isolated E2E stack intentionally has no external OpenAI credential.
 // Disable auto-generation here so this onboarding UI test does not pretend to
 // validate an external AI service with a mock response.
 await page.getByRole('button',{pressed:true}).click();
 await page.getByRole('button',{name:'ذخیره و ورود به پنل'}).click();
 await expect(page).toHaveURL(/\/fa\/app\/dashboard\?activation=chat-complete/);
 await expect(page.locator('main')).toContainText(/اولین خروجی|عملیات محتوا/);
 expect(runtimeErrors).toEqual([]);
});

test('authenticated tenant data is isolated and every primary module renders without runtime errors',async({page,request})=>{
 const ownerA=await createSession(request,'fa');
 const ownerB=await createSession(request,'fa');
 await seedWorkspace(request,ownerA.token);
 await seedWorkspace(request,ownerB.token);
 const secret=`tenant-secret-${unique('product')}`;
 const create=await request.post(`${API_URL}/brand-pulse/products`,{headers:authHeaders(ownerA.token),data:{name:secret,type:'service',description:'private tenant product',benefits:[],audience:'private',status:'active'}});
 expect(create.ok(),await create.text()).toBeTruthy();
 const otherOverview=await request.get(`${API_URL}/brand-pulse/overview`,{headers:authHeaders(ownerB.token)});
 expect(otherOverview.ok(),await otherOverview.text()).toBeTruthy();
 expect(JSON.stringify(await otherOverview.json())).not.toContain(secret);
 const anonymous=await request.get(`${API_URL}/dashboard/home`);
 expect(anonymous.status()).toBe(401);

 await installSession(page,ownerA.token);
 const runtimeErrors=captureRuntimeErrors(page);
 const failedResponses:string[]=[];
 page.on('response',response=>{if(response.status()>=500)failedResponses.push(`${response.status()} ${response.url()}`)});
 const modules=['dashboard','calendar','content-studio','approvals','campaigns','analytics','reports','brand-pulse','assets','integrations','settings','help'];
 for(const module of modules){
  const response=await page.goto(`/fa/app/${module}`,{waitUntil:'domcontentloaded'});
  expect(response?.status(),module).toBeLessThan(500);
  await expect(page.locator('main.app-content')).toBeVisible();
  await expect(page.locator('main')).toHaveCount(1);
  await expect(page.locator('body')).not.toContainText(/Application error|Internal Server Error|خطای داخلی سرور/i);
  if(module==='analytics')await expect(page.locator('body')).not.toContainText(/Connect analytics|Publish first content|Group content into campaigns|No insights yet/);
  if(module==='brand-pulse')await expect(page.locator('body')).not.toContainText(/Brand knowledge|Brand basics|Voice and style|Offer and positioning|Rules and compliance|Brand Pulse guide|Search collections|item\(s\)/);
  if(module==='integrations')await expect(page.locator('body')).not.toContainText(/Share authenticated or tokenized approval links|Send approvals and assisted publishing messages|Send approval requests to Bale|Assisted local publishing|No publishing connector connected|No analytics connector connected| · Easy| · Medium| · Hard/);
 }
 expect(failedResponses).toEqual([]);
 expect(runtimeErrors).toEqual([]);
});
