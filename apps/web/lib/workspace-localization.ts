type Locale='fa'|'en'|'de';

type SetupCopy={title:string;description?:string;action?:string};

const setupCopy:Record<Locale,Record<string,SetupCopy>>={
 fa:{
  create_brand:{title:'ساخت فضای برند',description:'اولین فضای برند را ایجاد کنید.',action:'ساخت برند'},
  brand_pulse:{title:'تکمیل پالس برند',description:'لحن، مخاطب، پیشنهادها و قوانین برند را ثبت کنید.',action:'تکمیل پالس برند'},
  product_service:{title:'افزودن محصول یا خدمت',description:'حداقل یک محصول، خدمت یا پیشنهاد قابل تبلیغ اضافه کنید.',action:'افزودن محصول یا خدمت'},
  channels:{title:'انتخاب کانال‌های محتوا',description:'کانال‌هایی را که می‌خواهید برایشان محتوا بسازید انتخاب کنید.',action:'انتخاب کانال‌ها'},
  content_channels:{title:'انتخاب کانال‌های محتوا',description:'کانال‌هایی را که می‌خواهید برایشان محتوا بسازید انتخاب کنید.',action:'انتخاب کانال‌ها'},
  approval:{title:'اتصال روش تأیید',description:'یک مسیر تأیید برای بررسی محتوا متصل کنید.',action:'اتصال روش تأیید'},
  approval_method:{title:'اتصال روش تأیید',description:'یک مسیر تأیید برای بررسی محتوا متصل کنید.',action:'اتصال روش تأیید'},
  generate_week:{title:'ساخت اولین برنامه هفتگی',description:'اولین برنامه محتوایی هفته را ایجاد کنید.',action:'ساخت برنامه هفتگی'},
  create_draft:{title:'ساخت اولین پیش‌نویس',description:'اولین محتوای واقعی برند را بنویسید یا تولید کنید.',action:'ساخت پیش‌نویس'},
  send_approval:{title:'ارسال اولین تأیید',description:'یک پیش‌نویس را برای بررسی ارسال کنید.',action:'ارسال برای تأیید'},
  publish_post:{title:'انتشار اولین محتوا',description:'محتوای تأییدشده را منتشر یا زمان‌بندی کنید.',action:'انتشار محتوا'},
  review_insight:{title:'بررسی اولین بینش',description:'پس از انتشار، عملکرد محتوا را بررسی کنید.',action:'مشاهده بینش‌ها'},
 },
 en:{
  create_brand:{title:'Create brand workspace'},brand_pulse:{title:'Complete Brand Pulse'},product_service:{title:'Add product or service'},channels:{title:'Choose content channels'},content_channels:{title:'Choose content channels'},approval:{title:'Connect an approval method'},approval_method:{title:'Connect an approval method'},generate_week:{title:'Generate the first week'},create_draft:{title:'Create the first draft'},send_approval:{title:'Send the first approval'},publish_post:{title:'Publish the first post'},review_insight:{title:'Review the first insight'},
 },
 de:{
  create_brand:{title:'Marken-Workspace erstellen',description:'Erstellen Sie Ihren ersten Marken-Workspace.',action:'Marke erstellen'},
  brand_pulse:{title:'Brand Pulse vervollständigen',description:'Erfassen Sie Tonalität, Zielgruppe, Angebote und Regeln.',action:'Brand Pulse vervollständigen'},
  product_service:{title:'Produkt oder Dienstleistung hinzufügen',description:'Fügen Sie mindestens ein vermarktbares Angebot hinzu.',action:'Angebot hinzufügen'},
  channels:{title:'Content-Kanäle auswählen',description:'Wählen Sie die Kanäle für Ihre Inhalte aus.',action:'Kanäle auswählen'},
  content_channels:{title:'Content-Kanäle auswählen',description:'Wählen Sie die Kanäle für Ihre Inhalte aus.',action:'Kanäle auswählen'},
  approval:{title:'Freigabemethode verbinden',description:'Verbinden Sie einen Prüf- und Freigabeweg.',action:'Freigabe verbinden'},
  approval_method:{title:'Freigabemethode verbinden',description:'Verbinden Sie einen Prüf- und Freigabeweg.',action:'Freigabe verbinden'},
  generate_week:{title:'Erste Woche planen'},create_draft:{title:'Ersten Entwurf erstellen'},send_approval:{title:'Erste Freigabe senden'},publish_post:{title:'Ersten Beitrag veröffentlichen'},review_insight:{title:'Erstes Insight prüfen'},
 }
};

const labels:Record<Locale,Record<string,Record<string,string>>>={
 fa:{
  language:{fa:'فارسی',en:'انگلیسی',de:'آلمانی'},
  channel:{instagram:'اینستاگرام',telegram:'تلگرام',bale:'بله',linkedin:'لینکدین',google_business:'پروفایل کسب‌وکار گوگل',email:'ایمیل',blog:'وبلاگ',facebook:'فیسبوک',youtube:'یوتیوب',tiktok:'تیک‌تاک',other:'سایر'},
  contentType:{post:'پست',reel:'ریلز',story:'استوری',carousel:'کاروسل',email:'ایمیل',blog:'مقاله وبلاگ',google_update:'به‌روزرسانی گوگل',telegram_post:'پست تلگرام',bale_post:'پست بله'},
  tone:{clear:'شفاف',professional:'حرفه‌ای',friendly:'صمیمی',formal:'رسمی',direct:'مستقیم',playful:'سرزنده'},
  transform:{rewrite:'بازنویسی',shorten:'کوتاه‌تر',more_formal:'رسمی‌تر',more_direct:'مستقیم‌تر'},
 },
 en:{language:{fa:'Persian',en:'English',de:'German'},channel:{},contentType:{},tone:{},transform:{rewrite:'Rewrite',shorten:'Shorten',more_formal:'More formal',more_direct:'More direct'}},
 de:{
  language:{fa:'Persisch',en:'Englisch',de:'Deutsch'},
  channel:{instagram:'Instagram',telegram:'Telegram',bale:'Bale',linkedin:'LinkedIn',google_business:'Google Unternehmensprofil',email:'E-Mail',blog:'Blog',facebook:'Facebook',youtube:'YouTube',tiktok:'TikTok',other:'Andere'},
  contentType:{post:'Beitrag',reel:'Reel',story:'Story',carousel:'Karussell',email:'E-Mail',blog:'Blogartikel',google_update:'Google-Update',telegram_post:'Telegram-Beitrag',bale_post:'Bale-Beitrag'},
  tone:{clear:'Klar',professional:'Professionell',friendly:'Freundlich',formal:'Formell',direct:'Direkt',playful:'Locker'},
  transform:{rewrite:'Neu formulieren',shorten:'Kürzen',more_formal:'Formeller',more_direct:'Direkter'},
 }
};

const normalizeLocale=(locale:string):Locale=>locale==='fa'||locale==='de'?locale:'en';

export function normalizeWorkspaceHref(href?:string){
 if(!href)return '/app/dashboard';
 return href.replace('/app/brand-pulse','/app/brand-pulse');
}

export function localizeSetupRequirement(locale:string,item:any){
 const lang=normalizeLocale(locale);const id=String(item?.id||'').toLowerCase();const copy=setupCopy[lang][id];
 return {
  ...item,
  title:copy?.title||item?.title||'',
  description:copy?.description||item?.description,
  action_label:copy?.action||item?.action_label,
  action_href:normalizeWorkspaceHref(item?.action_href),
 };
}

export function workspaceOptionLabel(locale:string,kind:'language'|'channel'|'contentType'|'tone'|'transform',value?:string){
 const lang=normalizeLocale(locale);const key=String(value||'');
 return labels[lang][kind]?.[key]||key.replaceAll('_',' ');
}

export function localizeRequirementList(locale:string,items:any[]|undefined){
 return (items||[]).map(item=>localizeSetupRequirement(locale,item));
}
