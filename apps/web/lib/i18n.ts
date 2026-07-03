export const locales = ['en', 'fa', 'de'] as const;
export type Locale = (typeof locales)[number];
export const isLocale = (v?: string): v is Locale => locales.includes(v as Locale);
export const dir = (locale: string) => locale === 'fa' ? 'rtl' : 'ltr';
export function switchLocalePath(pathname: string, next: Locale) {
  const parts = pathname.split('/').filter(Boolean);
  if (isLocale(parts[0])) parts[0] = next; else parts.unshift(next);
  return '/' + parts.join('/');
}
const shared = {
  en: { login:'Login', startDemo:'Start demo', approvalPreview:'Approval preview', search:'Search content, jobs, brands…', save:'Save', test:'Test', settings:'Settings', view:'View', approve:'Approve', reject:'Reject', requestChanges:'Request changes', generate:'Generate', connected:'Connected', mock:'Mock', needsSetup:'Needs setup' },
  de: { login:'Anmelden', startDemo:'Demo starten', approvalPreview:'Freigabevorschau', search:'Inhalte, Jobs, Marken suchen…', save:'Speichern', test:'Testen', settings:'Einstellungen', view:'Ansehen', approve:'Freigeben', reject:'Ablehnen', requestChanges:'Änderungen anfordern', generate:'Generieren', connected:'Verbunden', mock:'Demo', needsSetup:'Einrichtung nötig' },
  fa: { login:'ورود', startDemo:'شروع دمو', approvalPreview:'پیش‌نمایش تأیید', search:'جستجوی محتوا، کارها و برندها…', save:'ذخیره', test:'آزمایش', settings:'تنظیمات', view:'مشاهده', approve:'تأیید', reject:'رد', requestChanges:'درخواست تغییر', generate:'تولید', connected:'متصل', mock:'دمو', needsSetup:'نیازمند تنظیم' }
};
export const dict = {
  en: { ...shared.en, hero:'Your brand’s AI content manager', sub:'Plan, generate, approve, publish, analyze and learn from every content decision in one premium SaaS cockpit.', nav:['Product','Workflow','Integrations','Use cases','Pricing','FAQ'], cockpit:'Operating cockpit', dashboard:'Dashboard', admin:'Super Admin', modules:['Dashboard','Calendar','Content Studio','Approvals','Campaigns','Assets','Analytics','Brand DNA','Integrations','Reports','Settings','Super Admin'] },
  de: { ...shared.de, hero:'Der KI-Content-Manager für Ihre Marke', sub:'Planen, generieren, freigeben, veröffentlichen, analysieren und lernen – in einem hochwertigen SaaS-Cockpit.', nav:['Produkt','Workflow','Integrationen','Use Cases','Preise','FAQ'], cockpit:'Betriebscockpit', dashboard:'Dashboard', admin:'Super Admin', modules:['Dashboard','Kalender','Content Studio','Freigaben','Kampagnen','Assets','Analytics','Brand DNA','Integrationen','Reports','Einstellungen','Super Admin'] },
  fa: { ...shared.fa, hero:'مدیر محتوای هوشمند برند شما', sub:'برنامه‌ریزی، تولید، تأیید، انتشار، تحلیل و یادگیری از هر تصمیم محتوایی در یک کابین حرفه‌ای.', nav:['محصول','جریان کار','یکپارچه‌سازی‌ها','کاربردها','قیمت‌گذاری','پرسش‌ها'], cockpit:'کابین عملیات', dashboard:'داشبورد', admin:'سوپر ادمین', modules:['داشبورد','تقویم','استودیو محتوا','تأییدها','کمپین‌ها','دارایی‌ها','تحلیل‌ها','DNA برند','یکپارچه‌سازی‌ها','گزارش‌ها','تنظیمات','سوپر ادمین'] }
} as const;
export function t(locale: string) { return dict[isLocale(locale) ? locale : 'en']; }
