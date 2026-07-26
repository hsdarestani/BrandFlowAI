const faCategory:Record<string,string>={approval:'تأیید',publishing:'انتشار',analytics:'تحلیل',ecommerce:'فروشگاه',email:'ایمیل'};
const faDifficulty:Record<string,string>={easy:'آسان',medium:'متوسط',hard:'پیشرفته'};
const faFields:Record<string,string>={'Connection name':'نام اتصال','Bot token':'توکن ربات','Chat / channel ID':'شناسه گفت‌وگو یا کانال','API access key':'کلید دسترسی API','Bot ID':'شناسه ربات','Store URL':'آدرس فروشگاه','Consumer key':'کلید مصرف‌کننده','Consumer secret':'رمز مصرف‌کننده','API key':'کلید API','Sender email':'ایمیل فرستنده','Property ID':'شناسه پراپرتی','Service account JSON':'فایل JSON حساب سرویس'};

const faLabels:Record<string,string>={
 approval_link:'لینک عمومی تأیید',telegram:'ربات تلگرام',bale:'ربات بله',bale_safir:'بله سفیر',instagram:'اینستاگرام',facebook:'فیسبوک',linkedin:'لینکدین',google_business:'پروفایل کسب‌وکار گوگل',tiktok:'تیک‌تاک',youtube:'یوتیوب',ga4:'گوگل آنالیتیکس ۴',meta_insights:'بینش‌های متا',youtube_analytics:'تحلیل یوتیوب',woocommerce:'ووکامرس',brevo:'Brevo',mailchimp:'Mailchimp',email:'ایمیل',aparat:'آپارات',rubika:'روبیکا',eitaa:'ایتا',soroush:'سروش'
};

const faPurpose:Record<string,string>={
 approval_link:'ساخت و اشتراک لینک امن برای بررسی و تأیید محتوا',
 telegram:'ارسال درخواست تأیید و پیام‌های انتشار کمکی در تلگرام',
 bale:'ارسال درخواست‌های تأیید در بله',
 bale_safir:'ارسال اعلان و یادآوری از طریق بله سفیر',
 instagram:'آماده‌سازی محتوای اینستاگرام و انتشار کمکی تا زمان اتصال رسمی متا',
 facebook:'آماده‌سازی محتوای فیسبوک و انتشار کمکی',
 linkedin:'آماده‌سازی محتوای لینکدین و انتشار کمکی',
 google_business:'آماده‌سازی به‌روزرسانی پروفایل کسب‌وکار گوگل',
 tiktok:'آماده‌سازی ویدئوی کوتاه برای انتشار کمکی در تیک‌تاک',
 youtube:'آماده‌سازی انتشار و دریافت تحلیل‌های یوتیوب',
 ga4:'دریافت داده‌های واقعی تحلیل از گوگل آنالیتیکس ۴',
 meta_insights:'دریافت داده‌های عملکرد محتوا از متا',
 youtube_analytics:'دریافت داده‌های عملکرد کانال و ویدئوهای یوتیوب',
 woocommerce:'اتصال پیشنهادها، محصولات و داده سفارش‌های ووکامرس',
 brevo:'ارسال گزارش و پیام ایمیلی از طریق Brevo',
 mailchimp:'آماده‌سازی خروجی کمپین ایمیلی برای Mailchimp',
 email:'ارسال لینک‌های تأیید و گزارش از طریق ایمیل',
 aparat:'آماده‌سازی ویدئو برای انتشار کمکی در آپارات',
 rubika:'آماده‌سازی محتوا برای انتشار کمکی در روبیکا',
 eitaa:'آماده‌سازی محتوا برای انتشار کمکی در ایتا',
 soroush:'آماده‌سازی محتوا برای انتشار کمکی در سروش'
};

export function connectorCategoryLabel(locale:string,value:string){return locale==='fa'?(faCategory[value]||value):value}
export function connectorDifficultyLabel(locale:string,value:string){return locale==='fa'?(faDifficulty[value.toLowerCase()]||value):value}
export function connectorFieldLabel(locale:string,value:string){return locale==='fa'?(faFields[value]||value):value}

export function localizeConnectorItem(locale:string,item:any){
 if(locale!=='fa'||!item)return item;
 const provider=String(item.provider||item.id||'').toLowerCase();
 return {...item,label:faLabels[provider]||item.label,purpose:faPurpose[provider]||item.purpose,category:faCategory[item.category]||item.category,difficulty:faDifficulty[String(item.difficulty||'').toLowerCase()]||item.difficulty};
}

export function localizeConnectorNotice(locale:string,item:any){
 if(locale!=='fa'||!item)return item;
 const key=(String(item.id||'')+' '+String(item.title||'')).toLowerCase();
 if(key.includes('publishing'))return {...item,title:'هیچ مسیر انتشاری متصل نیست',description:'حداقل یک کانال انتشار یا بسته انتشار کمکی را تنظیم کنید.'};
 if(key.includes('analytics'))return {...item,title:'هیچ ابزار تحلیلی متصل نیست',description:'گوگل آنالیتیکس ۴ را متصل کنید یا متریک‌های واقعی را دستی وارد کنید.'};
 return item;
}
