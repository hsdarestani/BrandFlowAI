const faGroups:Record<string,string>={
 'Brand basics':'مشخصات پایه برند',
 'Audience':'مخاطب',
 'Voice and style':'لحن و سبک نوشتن',
 'Offer and positioning':'پیشنهاد و جایگاه‌سازی',
 'Rules and compliance':'قوانین و الزامات',
 'Content pillars':'ستون‌های محتوا',
};

const faFields:Record<string,string>={
 brand_name:'نام برند',website_url:'آدرس وب‌سایت',industry:'حوزه فعالیت',country:'کشور',primary_language:'زبان اصلی',timezone:'منطقه زمانی',brand_summary:'معرفی کوتاه برند',mission:'ماموریت',positioning:'جایگاه برند',target_audience:'مخاطب هدف',audience_pain_points:'دردها و مسئله‌های مخاطب',desired_outcomes:'نتیجه‌های مورد انتظار',buyer_objections:'اعتراض‌ها و تردیدهای خریدار',tone_of_voice:'لحن برند',writing_style:'سبک نوشتن',do_say:'عبارت‌های پیشنهادی',dont_say:'عبارت‌های ممنوع',cta_preferences:'ترجیحات دعوت به اقدام',hashtags_keywords:'هشتگ‌ها و کلیدواژه‌ها',value_propositions:'ارزش‌های پیشنهادی',differentiation:'وجه تمایز',competitors:'رقبا',proof_points:'شواهد و نقاط اثبات',forbidden_claims:'ادعاهای ممنوع',required_disclaimers:'توضیحات الزامی',approval_preferences:'ترجیحات تأیید',channel_notes:'نکات کانال‌ها',content_pillars:'ستون‌های محتوا',
};

export const brandPulseGroupLabel=(locale:string,key:string)=>locale==='fa'?(faGroups[key]||key):key;
export const brandPulseFieldLabel=(locale:string,key:string)=>locale==='fa'?(faFields[key]||key.replaceAll('_',' ')):key.replaceAll('_',' ');
export const brandPulseStatic=(locale:string,key:'knowledge'|'guide'|'search'|'items')=>{
 const values:any={
  en:{knowledge:'Brand knowledge',guide:'Brand Pulse guide',search:'Search collections',items:'items'},
  fa:{knowledge:'دانش برند',guide:'راهنمای پالس برند',search:'جست‌وجو در مجموعه‌ها',items:'مورد'},
  de:{knowledge:'Markenwissen',guide:'Brand-Pulse-Anleitung',search:'Sammlungen durchsuchen',items:'Einträge'},
 };
 return (values[locale]||values.en)[key];
};

export function localizeBrandPulseAction(locale:string,item:any){
 if(locale!=='fa'||!item)return item;
 const key=(String(item.id||'')+' '+String(item.title||'')+' '+String(item.action_label||'')).toLowerCase();
 if(key.includes('studio')||key.includes('content'))return {...item,title:'ساخت اولین محتوای برندمحور',description:'اطلاعات ثبت‌شده را در استودیوی محتوا به یک پیش‌نویس واقعی تبدیل کنید.',action_label:'باز کردن استودیوی محتوا'};
 if(key.includes('complete')||key.includes('pulse'))return {...item,title:'تکمیل پالس برند',description:'اطلاعات ناقص برند را تکمیل کنید تا تولید محتوا دقیق‌تر و هماهنگ‌تر شود.',action_label:'تکمیل پالس برند'};
 return item;
}
