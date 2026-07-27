type Locale='fa'|'en'|'de';

type SetupCopy={title:string;description?:string;action?:string;href?:string};

const setupCopy:Record<Locale,Record<string,SetupCopy>>={
 fa:{
  create_brand:{title:'ساخت فضای برند',description:'اولین فضای برند را ایجاد کنید.',action:'ساخت برند',href:'/onboarding'},
  brand_pulse:{title:'تکمیل پالس برند',description:'لحن، مخاطب، پیشنهادها و قوانین برند را ثبت کنید.',action:'تکمیل پالس برند',href:'/app/brand-pulse'},
  brand_basics:{title:'تکمیل مشخصات پایه برند',description:'وب‌سایت، حوزه فعالیت و معرفی کوتاه برند را ثبت کنید.',action:'تکمیل مشخصات برند',href:'/app/brand-pulse?section=basics'},
  audience:{title:'تعریف مخاطب هدف',description:'مخاطب هدف، مسئله‌ها و نتیجه‌های مطلوب او را مشخص کنید.',action:'تعریف مخاطب',href:'/app/brand-pulse?section=audience'},
  voice:{title:'تعریف لحن و سبک نوشتن',description:'لحن برند و شیوه نوشتن محتوا را مشخص کنید.',action:'تعریف لحن برند',href:'/app/brand-pulse?section=voice'},
  product_service:{title:'افزودن محصول یا خدمت',description:'حداقل یک محصول، خدمت یا پیشنهاد واقعی اضافه کنید.',action:'افزودن محصول یا خدمت',href:'/app/brand-pulse?section=offers'},
  brand_rule:{title:'افزودن قانون برند',description:'قوانین لحن، ادعاها و الزامات محتوا را ثبت کنید.',action:'افزودن قانون برند',href:'/app/brand-pulse?section=rules'},
  persona:{title:'افزودن پرسونا',description:'حداقل یک پرسونای مشخص برای مخاطب تعریف کنید.',action:'افزودن پرسونا',href:'/app/brand-pulse?section=personas'},
  memory_note:{title:'افزودن یادداشت حافظه',description:'یک یادگیری، بازخورد تأیید یا بینش مهم ثبت کنید.',action:'افزودن یادداشت',href:'/app/brand-pulse?section=memory'},
  content_channels:{title:'انتخاب کانال‌های محتوا',description:'کانال‌هایی را که می‌خواهید برایشان محتوا بسازید انتخاب کنید.',action:'انتخاب کانال‌ها',href:'/app/integrations'},
  approval_method:{title:'اتصال روش تأیید',description:'یک مسیر تأیید برای بررسی محتوا متصل کنید.',action:'اتصال روش تأیید',href:'/app/integrations?type=approval'},
  generate_week:{title:'ساخت اولین برنامه هفتگی',description:'اولین برنامه محتوایی هفته را ایجاد کنید.',action:'ساخت برنامه هفتگی',href:'/app/calendar?generate=1'},
  create_draft:{title:'ساخت اولین پیش‌نویس',description:'اولین محتوای واقعی برند را بنویسید یا تولید کنید.',action:'ساخت پیش‌نویس',href:'/app/content-studio?new=1'},
  send_approval:{title:'ارسال اولین تأیید',description:'یک پیش‌نویس را برای بررسی ارسال کنید.',action:'ارسال برای تأیید',href:'/app/content-studio?status=draft'},
  publish_post:{title:'انتشار اولین محتوا',description:'محتوای تأییدشده را منتشر یا زمان‌بندی کنید.',action:'انتشار محتوا',href:'/app/calendar?status=scheduled'},
  review_insight:{title:'بررسی اولین بینش',description:'پس از انتشار، عملکرد محتوا را بررسی کنید.',action:'مشاهده بینش‌ها',href:'/app/reports'},
 },
 en:{
  create_brand:{title:'Create brand workspace',href:'/onboarding'},
  brand_pulse:{title:'Complete Brand Pulse',description:'Add your audience, voice, offers, and brand rules.',href:'/app/brand-pulse'},
  brand_basics:{title:'Complete brand basics',description:'Add the website, industry, and brand summary.',href:'/app/brand-pulse?section=basics'},
  audience:{title:'Define the target audience',description:'Add the audience, pain points, and desired outcomes.',href:'/app/brand-pulse?section=audience'},
  voice:{title:'Define voice and writing style',description:'Add the brand tone and writing style.',href:'/app/brand-pulse?section=voice'},
  product_service:{title:'Add a product or service',description:'Add at least one real offer.',href:'/app/brand-pulse?section=offers'},
  brand_rule:{title:'Add a brand rule',description:'Add voice, claims, and compliance rules.',href:'/app/brand-pulse?section=rules'},
  persona:{title:'Add a persona',description:'Define at least one target persona.',href:'/app/brand-pulse?section=personas'},
  memory_note:{title:'Add a memory note',description:'Capture an approval learning or useful insight.',href:'/app/brand-pulse?section=memory'},
  content_channels:{title:'Choose content channels',href:'/app/integrations'},
  approval_method:{title:'Connect an approval method',href:'/app/integrations?type=approval'},
  generate_week:{title:'Generate the first week',href:'/app/calendar?generate=1'},
  create_draft:{title:'Create the first draft',href:'/app/content-studio?new=1'},
  send_approval:{title:'Send the first approval',href:'/app/content-studio?status=draft'},
  publish_post:{title:'Publish the first post',href:'/app/calendar?status=scheduled'},
  review_insight:{title:'Review the first insight',href:'/app/reports'},
 },
 de:{
  create_brand:{title:'Marken-Workspace erstellen',description:'Erstellen Sie Ihren ersten Marken-Workspace.',action:'Marke erstellen',href:'/onboarding'},
  brand_pulse:{title:'Brand Pulse vervollständigen',description:'Erfassen Sie Zielgruppe, Tonalität, Angebote und Regeln.',action:'Brand Pulse vervollständigen',href:'/app/brand-pulse'},
  brand_basics:{title:'Markengrundlagen vervollständigen',description:'Website, Branche und Kurzbeschreibung hinzufügen.',href:'/app/brand-pulse?section=basics'},
  audience:{title:'Zielgruppe definieren',description:'Zielgruppe, Probleme und gewünschte Ergebnisse erfassen.',href:'/app/brand-pulse?section=audience'},
  voice:{title:'Tonalität und Schreibstil definieren',description:'Markenton und Schreibstil festlegen.',href:'/app/brand-pulse?section=voice'},
  product_service:{title:'Produkt oder Dienstleistung hinzufügen',description:'Fügen Sie mindestens ein echtes Angebot hinzu.',action:'Angebot hinzufügen',href:'/app/brand-pulse?section=offers'},
  brand_rule:{title:'Markenregel hinzufügen',description:'Regeln für Tonalität, Aussagen und Compliance erfassen.',href:'/app/brand-pulse?section=rules'},
  persona:{title:'Persona hinzufügen',description:'Definieren Sie mindestens eine Zielpersona.',href:'/app/brand-pulse?section=personas'},
  memory_note:{title:'Memory-Notiz hinzufügen',description:'Erfassen Sie Feedback oder ein wichtiges Insight.',href:'/app/brand-pulse?section=memory'},
  content_channels:{title:'Content-Kanäle auswählen',description:'Wählen Sie die Kanäle für Ihre Inhalte aus.',action:'Kanäle auswählen',href:'/app/integrations'},
  approval_method:{title:'Freigabemethode verbinden',description:'Verbinden Sie einen Prüf- und Freigabeweg.',action:'Freigabe verbinden',href:'/app/integrations?type=approval'},
  generate_week:{title:'Erste Woche planen',href:'/app/calendar?generate=1'},
  create_draft:{title:'Ersten Entwurf erstellen',href:'/app/content-studio?new=1'},
  send_approval:{title:'Erste Freigabe senden',href:'/app/content-studio?status=draft'},
  publish_post:{title:'Ersten Beitrag veröffentlichen',href:'/app/calendar?status=scheduled'},
  review_insight:{title:'Erstes Insight prüfen',href:'/app/reports'},
 }
};

const aliases:Record<string,string>={
 channels:'content_channels',channel:'content_channels',approval:'approval_method',product:'product_service',offer:'product_service',rule:'brand_rule',memory:'memory_note',brand_dna:'brand_pulse',
};

const labels:Record<Locale,Record<string,Record<string,string>>>= {
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
 return href.replace('/app/brand-dna','/app/brand-pulse');
}

function requirementKey(item:any){
 const id=String(item?.id||'').toLowerCase().replaceAll('-','_');
 const raw=`${id} ${item?.title||''} ${item?.description||''}`.toLowerCase();
 if(id&&setupCopy.en[id])return id;
 if(aliases[id])return aliases[id];
 if(raw.includes('brand rule')||raw.includes('compliance, claims')||raw.includes('voice rules'))return 'brand_rule';
 if(raw.includes('memory note')||raw.includes('approval learning'))return 'memory_note';
 if(raw.includes('persona'))return 'persona';
 if(raw.includes('brand basics')||raw.includes('website, industry')||raw.includes('website industry'))return 'brand_basics';
 if(raw.includes('define audience')||raw.includes('target audience')||raw.includes('pain points'))return 'audience';
 if(raw.includes('set voice')||raw.includes('tone of voice')||raw.includes('writing style'))return 'voice';
 if(raw.includes('product/service')||raw.includes('product or service')||raw.includes('real offer')||raw.includes('no product'))return 'product_service';
 if(raw.includes('brand pulse')||raw.includes('brand dna'))return 'brand_pulse';
 if(raw.includes('approval method')||raw.includes('approval channel'))return 'approval_method';
 if(raw.includes('channel'))return 'content_channels';
 if(raw.includes('generate')&&raw.includes('week'))return 'generate_week';
 if(raw.includes('draft'))return 'create_draft';
 if(raw.includes('publish'))return 'publish_post';
 if(raw.includes('insight')||raw.includes('report'))return 'review_insight';
 return id;
}

export function localizeSetupRequirement(locale:string,item:any){
 const lang=normalizeLocale(locale);const key=requirementKey(item);const localized=setupCopy[lang][key];
 const existingHref=normalizeWorkspaceHref(item?.action_href);
 const genericHref=!item?.action_href||existingHref==='/onboarding'||existingHref==='/app/dashboard';
 return {
  ...item,
  id:item?.id||key,
  title:localized?.title||item?.title||'',
  description:localized?.description||item?.description,
  action_label:localized?.action||item?.action_label,
  action_href:genericHref&&localized?.href?localized.href:existingHref,
 };
}

export function workspaceOptionLabel(locale:string,kind:'language'|'channel'|'contentType'|'tone'|'transform',value?:string){
 const lang=normalizeLocale(locale);const key=String(value||'');
 return labels[lang][kind]?.[key]||key.replaceAll('_',' ');
}

export function localizeRequirementList(locale:string,items:any[]|undefined){
 return (items||[]).map(item=>localizeSetupRequirement(locale,item));
}
