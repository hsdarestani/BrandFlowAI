import {expect,test,type APIRequestContext,type Page} from '@playwright/test';

const API_URL=process.env.E2E_API_URL||'http://127.0.0.1:8000';
const unique=(prefix:string)=>`${prefix}-${Date.now()}-${Math.random().toString(36).slice(2,8)}`;

async function createSession(request:APIRequestContext){
 const email=`${unique('locale')}@example.com`;
 const response=await request.post(`${API_URL}/auth/signup`,{data:{name:'کاربر ترجمه',organization_name:`سازمان ${unique('locale')}`,email,password:'StrongPass123!',preferred_language:'fa',locale:'fa'}});
 expect(response.ok(),await response.text()).toBeTruthy();
 const payload=await response.json();
 return payload.access_token as string;
}

async function installSession(page:Page,token:string){
 await page.addInitScript(value=>{
  localStorage.setItem('smarbiz_token',value);
  localStorage.setItem('smarbiz_locale','fa');
 },token);
}

test('Persian Content Studio localizes dynamic setup requirements and controls',async({page,request})=>{
 const token=await createSession(request);
 await installSession(page,token);
 await page.goto('/fa/app/content-studio',{waitUntil:'domcontentloaded'});
 await expect(page.getByRole('heading',{name:'استودیوی محتوا',exact:true})).toBeVisible();
 await expect(page.getByText('ابتدا این مراحل را کامل کنید',{exact:true})).toBeVisible();
 await expect(page.getByText('افزودن محصول یا خدمت',{exact:true})).toBeVisible();
 await expect(page.getByText('تکمیل پالس برند',{exact:true})).toBeVisible();
 await expect(page.getByText('اتصال روش تأیید',{exact:true})).toBeVisible();
 const text=await page.locator('main.app-content').innerText();
 for(const stale of ['No product/service','Brand Pulse incomplete','No approval method','No channels selected','Compliance','Rewrite','Shorten','More formal','More direct','Translate…','Not saved','characters'])expect(text).not.toContain(stale);
});

test('legacy Brand DNA route opens the localized Brand Pulse workspace',async({page,request})=>{
 const token=await createSession(request);
 await installSession(page,token);
 await page.goto('/fa/app/brand-dna?section=offers',{waitUntil:'domcontentloaded'});
 await expect(page).toHaveURL(/\/fa\/app\/brand-pulse\?section=offers/);
 await expect(page.getByRole('heading',{name:'پالس برند',exact:true})).toBeVisible();
 const text=await page.locator('main.app-content').innerText();
 for(const stale of ['A living knowledge base','Complete Brand Pulse','Add product/service','Brand Pulse builder','Brand basics','Analyze website','Generate Brand Pulse','Cancel','Memory text','Preferred channels','Complete brand basics','Define audience','Set voice','Add brand rule','Add persona','Add memory note'])expect(text).not.toContain(stale);

 await page.getByRole('button',{name:/افزودن/}).first().click();
 const dialog=page.getByRole('dialog');
 await expect(dialog).toBeVisible();
 await expect(dialog).toContainText('نام');
 await expect(dialog).toContainText('نوع');
 await expect(dialog).toContainText('انصراف');
 await expect(dialog).not.toContainText(/Cancel|Name|Type|Status|Description/);
 await dialog.getByRole('button',{name:'بستن'}).click();
});

test('authenticated language switching replaces page copy without leaving stale Persian or English UI',async({page,request})=>{
 const token=await createSession(request);
 await installSession(page,token);
 await page.goto('/fa/app/brand-pulse',{waitUntil:'domcontentloaded'});
 await expect(page.getByRole('heading',{name:'پالس برند',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'English'}).click();
 await expect(page).toHaveURL(/\/en\/app\/brand-pulse/);
 await expect(page.getByRole('heading',{name:'Brand Pulse',exact:true})).toBeVisible();
 await expect(page.locator('main.app-content')).not.toContainText('سازنده دانش برند');
 await page.getByRole('button',{name:'Persian'}).click();
 await expect(page).toHaveURL(/\/fa\/app\/brand-pulse/);
 await expect(page.getByRole('heading',{name:'پالس برند',exact:true})).toBeVisible();
 await expect(page.locator('main.app-content')).not.toContainText('Brand knowledge builder');
});
