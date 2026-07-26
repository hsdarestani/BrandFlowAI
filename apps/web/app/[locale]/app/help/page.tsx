'use client';

import {use,useMemo,useState} from 'react';
import Link from 'next/link';
import {AppShell} from '@/components/app-shell';

const copy:any={
 en:{title:'Help Center',subtitle:'Short operating guides, not a wall of cards.',article:'How to operate this step',related:'Related actions',topics:['Getting started','Brand Pulse','Calendar','Content Studio','Approval flow','Direct vs assisted publishing','Telegram setup','Bale Bot setup','Bale Safir setup','Instagram limitations','Google Business','WooCommerce','Analytics and UTM','Super Admin'],steps:['Read the purpose.','Complete the related setup action.','Use the main action to continue the workflow.'],continue:'Continue setup',connect:'Connect an approval channel'},
 fa:{title:'مرکز راهنما',subtitle:'راهنماهای کوتاه و عملی برای انجام درست هر مرحله.',article:'این مرحله را چطور انجام بدهیم؟',related:'اقدام‌های مرتبط',topics:['شروع کار','پالس برند','تقویم محتوا','استودیوی محتوا','جریان تأیید','انتشار مستقیم و کمکی','راه‌اندازی تلگرام','راه‌اندازی ربات بله','راه‌اندازی بله سفیر','محدودیت‌های اینستاگرام','پروفایل کسب‌وکار گوگل','ووکامرس','تحلیل و UTM','مدیریت کل'],steps:['هدف این بخش را بخوانید.','تنظیم یا اقدام مرتبط را کامل کنید.','با دکمه اصلی، مسیر کار را ادامه دهید.'],continue:'ادامه راه‌اندازی',connect:'اتصال یک مسیر تأیید'},
 de:{title:'Hilfe-Center',subtitle:'Kurze praktische Anleitungen statt einer Wand aus Karten.',article:'So führen Sie diesen Schritt aus',related:'Zugehörige Aktionen',topics:['Erste Schritte','Brand Pulse','Kalender','Content Studio','Freigabeprozess','Direkte und assistierte Veröffentlichung','Telegram einrichten','Bale Bot einrichten','Bale Safir einrichten','Instagram-Einschränkungen','Google Unternehmensprofil','WooCommerce','Analytics und UTM','Super Admin'],steps:['Lesen Sie den Zweck dieses Bereichs.','Schließen Sie die zugehörige Einrichtung oder Aktion ab.','Fahren Sie mit der Hauptaktion im Workflow fort.'],continue:'Setup fortsetzen',connect:'Freigabekanal verbinden'}
};

export default function Page({params}:{params:Promise<{locale:string}>}){
 const {locale}=use(params);
 return <AppShell locale={locale}><Help locale={locale}/></AppShell>;
}

function Help({locale}:{locale:string}){
 const c=copy[locale]||copy.en;
 const [topicIndex,setTopicIndex]=useState(0);
 const topic=useMemo(()=>c.topics[topicIndex]||c.topics[0],[c,topicIndex]);
 return <div className="grid gap-6 lg:grid-cols-[18rem_1fr_18rem]">
  <aside className="panel p-4"><h1 className="mb-2 text-2xl font-black">{c.title}</h1><p className="muted mb-4 text-sm">{c.subtitle}</p>{c.topics.map((label:string,index:number)=><button className={`block w-full rounded-xl p-3 text-start transition ${index===topicIndex?'bg-blue-50 font-bold text-blue-800':'hover:bg-slate-50'}`} onClick={()=>setTopicIndex(index)} key={label}>{label}</button>)}</aside>
  <article className="panel p-8"><p className="badge">{topic}</p><h2 className="mt-4 text-4xl font-black">{c.article}</h2><p className="muted mt-4">{c.subtitle}</p><ol className="mt-6 list-decimal space-y-3 ps-6">{c.steps.map((step:string)=><li key={step}>{step}</li>)}</ol></article>
  <aside className="learning-card p-5"><h3 className="font-black">{c.related}</h3><div className="mt-4 flex flex-col gap-2"><Link className="chip" href={`/${locale}/onboarding`}>{c.continue}</Link><Link className="chip" href={`/${locale}/app/integrations`}>{c.connect}</Link></div></aside>
 </div>;
}
