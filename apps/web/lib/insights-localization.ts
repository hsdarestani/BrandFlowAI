export type LocalizedInsightItem={
 id?:string;
 title?:string;
 description?:string;
 action_label?:string;
 [key:string]:unknown;
};

export function localizeInsightItem(locale:string,item:LocalizedInsightItem):LocalizedInsightItem{
 if(locale!=='fa'||!item)return item;
 const key=(String(item.id||'')+' '+String(item.title||'')).toLowerCase();
 if(key.includes('analytics'))return {...item,title:'اتصال ابزار تحلیل',description:'GA4 یا ابزار تحلیل پلتفرم را متصل کنید؛ در غیر این صورت متریک‌های واقعی را دستی ثبت کنید.',action_label:'اتصال تحلیل'};
 if(key.includes('publish'))return {...item,title:'انتشار اولین محتوا',description:'بعد از انتشار یا زمان‌بندی اولین محتوا، بینش‌ها دقیق‌تر و کاربردی‌تر می‌شوند.',action_label:'باز کردن استودیوی محتوا'};
 if(key.includes('campaign'))return {...item,title:'گروه‌بندی محتوا در کمپین‌ها',description:'اتصال محتوا به کمپین‌ها، مقایسه عملکرد و یادگیری از نتایج را ساده‌تر می‌کند.',action_label:'ساخت کمپین'};
 if(key.includes('no insight'))return {...item,title:'هنوز بینشی وجود ندارد',description:'یک ابزار تحلیل متصل کنید یا اولین متریک واقعی را دستی ثبت کنید.'};
 return item;
}
