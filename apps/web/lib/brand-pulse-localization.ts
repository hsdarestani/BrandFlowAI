const groups:Record<string,Record<string,string>>={
 fa:{
  'Brand basics':'مشخصات پایه برند','Audience':'مخاطب','Voice and style':'لحن و سبک نوشتن','Offer and positioning':'پیشنهاد و جایگاه‌سازی','Rules and compliance':'قوانین و الزامات','Content pillars':'ستون‌های محتوا',
 },
 de:{
  'Brand basics':'Markengrundlagen','Audience':'Zielgruppe','Voice and style':'Tonalität und Schreibstil','Offer and positioning':'Angebot und Positionierung','Rules and compliance':'Regeln und Compliance','Content pillars':'Content-Säulen',
 },
};

const fields:Record<string,Record<string,string>>={
 fa:{
  brand_name:'نام برند',website_url:'آدرس وب‌سایت',industry:'حوزه فعالیت',country:'کشور',primary_language:'زبان اصلی',timezone:'منطقه زمانی',brand_summary:'معرفی کوتاه برند',mission:'ماموریت',positioning:'جایگاه برند',target_audience:'مخاطب هدف',audience_pain_points:'دردها و مسئله‌های مخاطب',desired_outcomes:'نتیجه‌های مورد انتظار',buyer_objections:'اعتراض‌ها و تردیدهای خریدار',tone_of_voice:'لحن برند',writing_style:'سبک نوشتن',do_say:'عبارت‌های پیشنهادی',dont_say:'عبارت‌های ممنوع',cta_preferences:'ترجیحات دعوت به اقدام',hashtags_keywords:'هشتگ‌ها و کلیدواژه‌ها',value_propositions:'ارزش‌های پیشنهادی',differentiation:'وجه تمایز',competitors:'رقبا',proof_points:'شواهد و نقاط اثبات',forbidden_claims:'ادعاهای ممنوع',required_disclaimers:'توضیحات الزامی',approval_preferences:'ترجیحات تأیید',channel_notes:'نکات کانال‌ها',content_pillars:'ستون‌های محتوا',
 },
 de:{
  brand_name:'Markenname',website_url:'Website-URL',industry:'Branche',country:'Land',primary_language:'Hauptsprache',timezone:'Zeitzone',brand_summary:'Kurzbeschreibung der Marke',mission:'Mission',positioning:'Positionierung',target_audience:'Zielgruppe',audience_pain_points:'Probleme der Zielgruppe',desired_outcomes:'Gewünschte Ergebnisse',buyer_objections:'Kauf-Einwände',tone_of_voice:'Markenton',writing_style:'Schreibstil',do_say:'Empfohlene Formulierungen',dont_say:'Verbotene Formulierungen',cta_preferences:'CTA-Präferenzen',hashtags_keywords:'Hashtags und Keywords',value_propositions:'Wertversprechen',differentiation:'Differenzierung',competitors:'Wettbewerber',proof_points:'Nachweise',forbidden_claims:'Verbotene Aussagen',required_disclaimers:'Erforderliche Hinweise',approval_preferences:'Freigabepräferenzen',channel_notes:'Kanalhinweise',content_pillars:'Content-Säulen',
 },
};

export const brandPulseGroupLabel=(locale:string,key:string)=>groups[locale]?.[key]||key;
export const brandPulseFieldLabel=(locale:string,key:string)=>fields[locale]?.[key]||key.replaceAll('_',' ');

export const brandPulseStatic=(locale:string,key:'knowledge'|'guide'|'search'|'items')=>{
 const values:any={
  en:{knowledge:'Brand knowledge',guide:'Brand Pulse guide',search:'Search collections',items:'items'},
  fa:{knowledge:'دانش برند',guide:'راهنمای پالس برند',search:'جست‌وجو در مجموعه‌ها',items:'مورد'},
  de:{knowledge:'Markenwissen',guide:'Brand-Pulse-Anleitung',search:'Sammlungen durchsuchen',items:'Einträge'},
 };
 return (values[locale]||values.en)[key];
};

export function localizeBrandPulseAction(locale:string,item:any){
 if(!item||locale==='en')return item;
 const key=(String(item.id||'')+' '+String(item.title||'')+' '+String(item.action_label||'')).toLowerCase();
 if(locale==='fa'){
  if(key.includes('studio')||key.includes('content'))return {...item,title:'ساخت اولین محتوای برندمحور',description:'اطلاعات ثبت‌شده را در استودیوی محتوا به یک پیش‌نویس واقعی تبدیل کنید.',action_label:'بازکردن استودیوی محتوا'};
  if(key.includes('complete')||key.includes('pulse'))return {...item,title:'تکمیل پالس برند',description:'اطلاعات ناقص برند را تکمیل کنید تا تولید محتوا دقیق‌تر و هماهنگ‌تر شود.',action_label:'تکمیل پالس برند'};
 }
 if(locale==='de'){
  if(key.includes('studio')||key.includes('content'))return {...item,title:'Ersten markengerechten Inhalt erstellen',description:'Verwandeln Sie das gespeicherte Markenwissen im Content Studio in einen echten Entwurf.',action_label:'Content Studio öffnen'};
  if(key.includes('complete')||key.includes('pulse'))return {...item,title:'Brand Pulse vervollständigen',description:'Vervollständigen Sie fehlende Markenangaben für präzisere Inhalte.',action_label:'Brand Pulse vervollständigen'};
 }
 return item;
}
