import {localizeRequirementList,normalizeWorkspaceHref} from './workspace-localization';

type Locale='fa'|'en'|'de';
const lang=(locale:string):Locale=>locale==='fa'||locale==='de'?locale:'en';

const phrases:Record<Locale,Record<string,string>>={
 fa:{
  'not connected':'متصل نیست','connected':'متصل','Short Video':'ویدئوی کوتاه','Clear filters':'پاک‌کردن فیلترها','Missing dates':'بدون تاریخ',
  'Plan your first content week':'اولین هفته محتوایی را برنامه‌ریزی کنید','Generate or create your first content items.':'اولین آیتم‌های محتوا را تولید یا دستی ایجاد کنید.',
  'Complete setup':'تکمیل راه‌اندازی','Resolve missing setup steps.':'مراحل ناقص راه‌اندازی را کامل کنید.',
  'Brand Pulse not completed':'پالس برند تکمیل نشده است','No product/service added':'محصول یا خدمتی اضافه نشده است','No product/service':'محصول یا خدمتی اضافه نشده است',
  'No channels selected':'کانالی انتخاب نشده است','No approval method connected':'روش تأییدی متصل نیست','Enable public approval link or connect Telegram/Bale.':'لینک عمومی تأیید را فعال کنید یا تلگرام/بله را متصل کنید.',
  'No connected channels':'هیچ کانالی متصل نیست','Connect a publishing or approval channel.':'یک کانال انتشار یا روش تأیید متصل کنید.','Missing approval channel':'مسیر تأیید ناقص است','Connect at least one approval method.':'حداقل یک روش تأیید متصل کنید.',
  'No performance data yet':'هنوز داده عملکردی ثبت نشده است','No approval decisions yet':'هنوز تصمیم تأییدی ثبت نشده است',
  'Report missing performance data':'داده عملکرد گزارش ناقص است','Add manual metrics or connect analytics for stronger reports.':'برای گزارش دقیق‌تر، متریک واقعی را دستی وارد کنید یا ابزار تحلیل را متصل کنید.',
  'Next step':'قدم بعدی','Create your first weekly content plan.':'اولین برنامه هفتگی محتوا را ایجاد کنید.','No content generated':'هنوز محتوایی ساخته نشده است','Generate your first week to start tracking activity.':'برای شروع ثبت فعالیت، اولین هفته محتوا را بسازید.',
  'Add brand rule':'افزودن قانون برند','Add compliance, claims, or voice rules.':'قوانین لحن، ادعاها و الزامات محتوا را ثبت کنید.','Add rule':'افزودن قانون',
  'Add persona':'افزودن پرسونا','Define one target persona.':'حداقل یک پرسونای هدف تعریف کنید.','Add memory note':'افزودن یادداشت حافظه','Capture an approval learning or insight.':'یک بازخورد تأیید یا بینش مهم ثبت کنید.',
  'Complete brand basics':'تکمیل مشخصات پایه برند','Add website, industry, and summary.':'وب‌سایت، حوزه فعالیت و معرفی کوتاه برند را ثبت کنید.','Define audience':'تعریف مخاطب هدف','Add target audience and pain points.':'مخاطب هدف و مسئله‌های او را ثبت کنید.','Set voice':'تعریف لحن برند','Add tone of voice and writing style.':'لحن و سبک نوشتن برند را مشخص کنید.',
  'Approval notes':'نکات تأیید','Channel rules':'قوانین کانال‌ها','approval link':'لینک تأیید','Approval link':'لینک تأیید',
  'All statuses':'همه وضعیت‌ها','Search campaigns':'جست‌وجوی کمپین‌ها','No matching campaigns':'کمپینی با این فیلتر پیدا نشد','No goal':'بدون هدف','No description':'بدون توضیحات','Open Studio':'بازکردن استودیو','Open Calendar':'بازکردن تقویم','Ideas':'ایده‌ها','Drafts':'پیش‌نویس‌ها','Scheduled':'زمان‌بندی‌شده','Published':'منتشرشده','Draft':'پیش‌نویس','Calendar':'تقویم',
  'Search reports':'جست‌وجوی گزارش‌ها','Loading settings…':'در حال بارگذاری تنظیمات…',
 },
 de:{
  'not connected':'Nicht verbunden','connected':'Verbunden','Short Video':'Kurzvideo','Clear filters':'Filter zurücksetzen','Missing dates':'Fehlende Termine',
  'Plan your first content week':'Planen Sie Ihre erste Content-Woche','Generate or create your first content items.':'Generieren oder erstellen Sie Ihre ersten Inhalte.',
  'Complete setup':'Setup abschließen','Resolve missing setup steps.':'Schließen Sie die fehlenden Setup-Schritte ab.',
  'Brand Pulse not completed':'Brand Pulse ist nicht vollständig','No product/service added':'Kein Produkt oder Service hinzugefügt','No channels selected':'Keine Kanäle ausgewählt','No approval method connected':'Keine Freigabemethode verbunden',
  'No connected channels':'Keine Kanäle verbunden','Connect a publishing or approval channel.':'Verbinden Sie einen Publishing- oder Freigabekanal.','Missing approval channel':'Freigabekanal fehlt','Connect at least one approval method.':'Verbinden Sie mindestens eine Freigabemethode.',
  'No performance data yet':'Noch keine Performance-Daten','No approval decisions yet':'Noch keine Freigabeentscheidungen','Report missing performance data':'Performance-Daten im Bericht fehlen','Add manual metrics or connect analytics for stronger reports.':'Fügen Sie echte Metriken hinzu oder verbinden Sie Analytics.',
  'Next step':'Nächster Schritt','Create your first weekly content plan.':'Erstellen Sie Ihren ersten wöchentlichen Content-Plan.','No content generated':'Noch keine Inhalte generiert','Generate your first week to start tracking activity.':'Generieren Sie die erste Woche, um Aktivitäten zu verfolgen.',
  'Add brand rule':'Markenregel hinzufügen','Add compliance, claims, or voice rules.':'Regeln für Tonalität, Aussagen und Compliance hinzufügen.','Add rule':'Regel hinzufügen',
  'Approval notes':'Freigabehinweise','Channel rules':'Kanalregeln','approval link':'Freigabelink','Approval link':'Freigabelink',
  'All statuses':'Alle Status','Search campaigns':'Kampagnen suchen','No matching campaigns':'Keine passende Kampagne','No goal':'Kein Ziel','No description':'Keine Beschreibung','Open Studio':'Studio öffnen','Open Calendar':'Kalender öffnen','Ideas':'Ideen','Drafts':'Entwürfe','Scheduled':'Geplant','Published':'Veröffentlicht','Draft':'Entwurf','Calendar':'Kalender','Search reports':'Berichte suchen','Loading settings…':'Einstellungen werden geladen…',
 },
 en:{}
};

function dictionaryLookup(locale:string,value:string){
 const dictionary=phrases[lang(locale)];
 const trimmed=value.trim();
 const exact=dictionary[trimmed];
 if(exact)return exact;
 const lower=trimmed.toLowerCase();
 const match=Object.entries(dictionary).find(([key])=>key.toLowerCase()===lower);
 return match?.[1]||value;
}

export function localizeKnownText(locale:string,value:any){
 if(typeof value!=='string'||locale==='en')return value;
 return dictionaryLookup(locale,value);
}

export function deepLocalizeKnownCopy<T>(locale:string,value:T):T{
 if(locale==='en'||value==null)return value;
 if(typeof value==='string')return localizeKnownText(locale,value) as T;
 if(Array.isArray(value))return value.map(item=>deepLocalizeKnownCopy(locale,item)) as T;
 if(typeof value==='object'){
  const output:any={};
  for(const [key,item] of Object.entries(value as any))output[key]=deepLocalizeKnownCopy(locale,item);
  return output;
 }
 return value;
}

export function localizeWorkspacePayload<T extends any>(locale:string,value:T):T{
 const output:any=deepLocalizeKnownCopy(locale,value);
 if(output?.setup?.missing_requirements)output.setup.missing_requirements=localizeRequirementList(locale,output.setup.missing_requirements);
 if(output?.setup?.steps)output.setup.steps=localizeRequirementList(locale,output.setup.steps);
 if(output?.recommended_action){
  output.recommended_action=deepLocalizeKnownCopy(locale,output.recommended_action);
  output.recommended_action.action_href=normalizeWorkspaceHref(output.recommended_action.action_href);
 }
 if(output?.alerts)output.alerts=deepLocalizeKnownCopy(locale,output.alerts).map((item:any)=>({...item,href:normalizeWorkspaceHref(item.href)}));
 return output;
}

export function localizeStudioRule(locale:string,rule:any){
 if(!rule||locale==='en')return rule;
 const raw=`${rule.label||''} ${rule.description||''}`.toLowerCase();
 if(locale==='fa'){
  if(raw.includes('approval link'))return {...rule,label:'لینک تأیید',description:'از لینک عمومی تأیید برای بررسی امن محتوا استفاده کنید.'};
  if(raw.includes('approval note'))return {...rule,label:'نکات تأیید',description:localizeKnownText(locale,rule.description)};
  if(raw.includes('channel rule'))return {...rule,label:'قوانین کانال‌ها',description:localizeKnownText(locale,rule.description)};
 }
 if(locale==='de'){
  if(raw.includes('approval link'))return {...rule,label:'Freigabelink',description:'Nutzen Sie den öffentlichen Freigabelink für eine sichere Inhaltsprüfung.'};
  if(raw.includes('approval note'))return {...rule,label:'Freigabehinweise',description:localizeKnownText(locale,rule.description)};
  if(raw.includes('channel rule'))return {...rule,label:'Kanalregeln',description:localizeKnownText(locale,rule.description)};
 }
 return {...rule,label:localizeKnownText(locale,rule.label),description:localizeKnownText(locale,rule.description)};
}

const metricLabels:Record<Locale,Record<string,string>>={
 fa:{drafts_created:'پیش‌نویس‌های ساخته‌شده',approvals_sent:'ارسال‌شده برای تأیید',approvals_approved:'تأییدشده',scheduled_posts:'محتوای زمان‌بندی‌شده',published_posts:'محتوای منتشرشده',campaigns:'کمپین‌ها',manual_metrics:'متریک‌های دستی',performance_data:'داده عملکرد',total_items:'مجموع آیتم‌ها',approval_rate:'نرخ تأیید'},
 de:{drafts_created:'Erstellte Entwürfe',approvals_sent:'Gesendete Freigaben',approvals_approved:'Freigegeben',scheduled_posts:'Geplante Beiträge',published_posts:'Veröffentlichte Beiträge',campaigns:'Kampagnen',manual_metrics:'Manuelle Metriken',performance_data:'Performance-Daten',total_items:'Einträge gesamt',approval_rate:'Freigaberate'},
 en:{}
};
export function localizeMetricLabel(locale:string,key:string){return metricLabels[lang(locale)][key]||key.replaceAll('_',' ')}

export function connectionStateLabel(locale:string,connected:boolean){return connected?(locale==='fa'?'متصل':locale==='de'?'Verbunden':'connected'):(locale==='fa'?'متصل نیست':locale==='de'?'Nicht verbunden':'not connected')}
