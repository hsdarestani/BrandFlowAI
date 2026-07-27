'use client';

import Link from 'next/link';
import {t} from '@/lib/i18n';
import {useToast} from './ui/toast';

const guideCopy:any={
 en:{what:'What this page is for',first:'First action',firstText:'Complete the essential inputs and create one real output.',best:'Best practice',bestText:'Follow the workflow step by step and review every output before publishing.',mistake:'Common mistake',mistakeText:'Do not publish before approval.',help:'Open Help Center'},
 fa:{what:'کاربرد این صفحه',first:'اولین اقدام',firstText:'اطلاعات ضروری را کامل کنید و یک خروجی واقعی بسازید.',best:'بهترین روش',bestText:'مسیر را مرحله‌به‌مرحله جلو ببرید و هر خروجی را پیش از انتشار بررسی کنید.',mistake:'اشتباه رایج',mistakeText:'قبل از تأیید، محتوا را منتشر نکنید.',help:'بازکردن مرکز راهنما'},
 de:{what:'Wofür diese Seite gedacht ist',first:'Erster Schritt',firstText:'Vervollständigen Sie die wichtigsten Angaben und erstellen Sie ein echtes Ergebnis.',best:'Empfohlene Vorgehensweise',bestText:'Folgen Sie dem Ablauf Schritt für Schritt und prüfen Sie jedes Ergebnis vor der Veröffentlichung.',mistake:'Häufiger Fehler',mistakeText:'Veröffentlichen Sie Inhalte nicht vor der Freigabe.',help:'Help Center öffnen'}
};

const pageNames:any={
 fa:{'Content Studio':'استودیوی محتوا','Content Calendar':'تقویم محتوا','Calendar':'تقویم محتوا','Campaigns':'کمپین‌ها','Reports':'گزارش‌ها','Integrations':'اتصال‌ها','Brand Pulse':'پالس برند','Assets':'فایل‌ها و دارایی‌ها','Settings':'تنظیمات'},
 de:{'Content Studio':'Content Studio','Content Calendar':'Content-Kalender','Calendar':'Content-Kalender','Campaigns':'Kampagnen','Reports':'Berichte','Integrations':'Integrationen','Brand Pulse':'Brand Pulse','Assets':'Assets','Settings':'Einstellungen'}
};

export function HelpAside({locale,page}:{locale:string;page:string}){
 const c=guideCopy[locale]||guideCopy.en;
 const title=pageNames[locale]?.[page]||page;
 return <aside className="learning-card p-5"><p className="badge">{c.what}</p><h3 className="mt-3 text-xl font-black">{title}</h3><dl className="mt-4 space-y-3 text-sm"><div><dt className="font-bold">{c.first}</dt><dd className="muted">{c.firstText}</dd></div><div><dt className="font-bold">{c.best}</dt><dd className="muted">{c.bestText}</dd></div><div><dt className="font-bold">{c.mistake}</dt><dd className="muted">{c.mistakeText}</dd></div></dl><Link className="chip mt-4" href={`/${locale}/app/help`}>{c.help}</Link></aside>;
}

export function SetupChecklist({locale}:{locale:string}){const d=t(locale);const toast=useToast();const statuses=['done','done','inProgress','notStarted','notStarted','notStarted','notStarted','notStarted','notStarted','notStarted'];return <section className="panel p-5"><div className="flex items-end justify-between gap-3"><div><h2 className="text-2xl font-black">{d.checklist.title}</h2><p className="muted">{d.checklist.assistantText}</p></div><b className="text-3xl">24%</b></div><div className="mt-4 divide-y divide-white/10">{d.checklist.items.map((item:string,i:number)=><div className="flex flex-wrap items-center gap-3 py-3" key={item}><span className="badge">{(d.statuses as any)[statuses[i]]}</span><b className="min-w-48">{item}</b><span className="muted flex-1 text-sm">{d.checklist.why[i]} · {i+2} {d.checklist.minutes}</span><button className="chip" onClick={()=>toast(item)}>{d.actions.open}</button></div>)}</div></section>}
export function EmptyStateGuide({locale,title,cta,href}:{locale:string;title:string;cta:string;href:string}){const d=t(locale);return <div className="command-card p-8 text-center"><h2 className="text-3xl font-black">{title}</h2><p className="muted mx-auto mt-2 max-w-xl">{d.checklist.assistantText}</p><Link className="btn mt-5" href={href}>{cta}</Link></div>}
export const SectionGuide=HelpAside;
export function HelpTooltip({label}:{label:string;tip:string}){return <span>{label}</span>}
export function ActionModal(){return null}
