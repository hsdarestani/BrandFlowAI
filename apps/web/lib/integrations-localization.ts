const faCategory:Record<string,string>={approval:'تأیید',publishing:'انتشار',analytics:'تحلیل',ecommerce:'فروشگاه',email:'ایمیل'};
const faDifficulty:Record<string,string>={easy:'آسان',medium:'متوسط',hard:'پیشرفته'};

const faPurpose:Record<string,string>={
 approval_link:'ساخت و اشتراک لینک امن برای بررسی و تأیید محتوا',
 telegram:'ارسال درخواست تأیید و پیام‌های انتشار کمکی در تلگرام',
 bale:'ارسال درخواست‌های تأیید در بله',
 bale_safir:'ارسال اعلان و یادآوری از طریق بله سفیر',
 instagram:'آماده‌سازی محتوای اینستاگرام و انتشار کمکی تا زمان اتصال رسمی متا',
 facebook:'آماده‌سازی محتوای فیسبوک و انتشار کمکی',
 linkedin:'آماده‌سازی محتوای لینکدین و انتشار کمکی',
 google_business:'آماده‌سازی به‌روزرسانی پروفایل کسب‌وکار گوگل',
 woocommerce:'اتصال پیشنهادها، محصولات و داده سفارش‌های ووکامرس',
 ga4:'دریافت داده‌های واقعی تحلیل از گوگل آنالیتیکس ۴',
 brevo:'ارسال گزارش و پیام ایمیلی از طریق Brevo',
 email:'ارسال لینک‌های تأیید و گزارش از طریق ایمیل',
 aparat:'آماده‌سازی ویدئو برای انتشار کمکی در آپارات',
 rubika:'آماده‌سازی محتوا برای انتشار کمکی در روبیکا',
 eitaa:'آماده‌سازی محتوا برای انتشار کمکی در ایتا',
};

export function connectorCategoryLabel(locale:string,value:string){return locale==='fa'?(faCategory[value]||value):value}
export function connectorDifficultyLabel(locale:string,value:string){return locale==='fa'?(faDifficulty[value.toLowerCase()]||value):value}

export function localizeConnectorItem(locale:string,item:any){
 if(locale!=='fa'||!item)return item;
 const provider=String(item.provider||item.id||'').toLowerCase();
 return {...item,purpose:faPurpose[provider]||item.purpose,category:faCategory[item.category]||item.category,difficulty:faDifficulty[String(item.difficulty||'').toLowerCase()]||item.difficulty};
}

export function localizeConnectorNotice(locale:string,item:any){
 if(locale!=='fa'||!item)return item;
 const key=(String(item.id||'')+' '+String(item.title||'')).toLowerCase();
 if(key.includes('publishing'))return {...item,title:'هیچ مسیر انتشاری متصل نیست',description:'حداقل یک کانال انتشار یا بسته انتشار کمکی را تنظیم کنید.'};
 if(key.includes('analytics'))return {...item,title:'هیچ ابزار تحلیلی متصل نیست',description:'GA4 را متصل کنید یا متریک‌های واقعی را دستی وارد کنید.'};
 return item;
}
