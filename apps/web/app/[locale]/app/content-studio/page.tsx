'use client';

import {use, useEffect, useMemo, useState} from 'react';
import {useRouter, useSearchParams} from 'next/navigation';
import {AppShell} from '@/components/app-shell';
import {HelpAside} from '@/components/product-guidance';
import {useToast} from '@/components/ui/toast';
import {api} from '@/lib/api';
import {statusLabel} from '@/lib/i18n';

type Severity='info'|'warning'|'danger';
type StudioWarning={id:string;title:string;description:string;severity:Severity};
type StudioDraft={
  id:number|string;title:string;body:string;hook?:string;cta?:string;hashtags?:string;goal?:string;
  channel?:string;language?:string;content_type?:string;product_or_offer?:string;tone?:string;prompt?:string;
  status:'draft'|'in_review'|'approved'|'scheduled'|'published'|'archived';quality_score?:number|null;
  warnings?:StudioWarning[];compliance_result?:{status:'passed'|'warnings'|'blocked';summary:string;warnings:any[];suggestions:string[]}|null;updated_at?:string
};
type StudioOverview={
  user:{id:number;name:string;email:string};organization:{id:number;name:string}|null;
  brand:{id:number;name:string;primary_language?:string;industry?:string}|null;
  setup:{can_generate:boolean;missing_requirements:{id:string;title:string;action_href:string}[]};drafts:StudioDraft[];
  brand_rules:{id:string;label:string;description:string;severity:Severity}[];
  recommended_action:{title:string;description:string;action_label:string;action_type:'generate'|'navigate'|'check'|'approval'|'schedule';action_href?:string};
  products?:string[];channels?:string[]
};

const blankDraft=(language='en'):StudioDraft=>({id:'',title:'',body:'',hook:'',cta:'',hashtags:'',goal:'',channel:'instagram',language,content_type:'post',product_or_offer:'',tone:'clear',prompt:'',status:'draft'});
const copies:any={
 en:{title:'Content Studio',sub:'Turn a real brief and Brand Pulse into a reviewable, platform-ready draft.',none:'No draft selected yet.',generate:'Generate draft',blank:'New blank draft',save:'Save',unsaved:'Unsaved changes',saved:'Saved',brief:'Brief',rules:'Brand rules',preview:'Platform preview',missing:'Missing setup requirements',compliance:'Compliance check',approval:'Send for approval',schedule:'Schedule',export:'Export assisted kit',archive:'Archive',recent:'Recent drafts',search:'Search drafts',goal:'Goal',channel:'Channel',language:'Language',type:'Content type',offer:'Product / offer',tone:'Tone',prompt:'Prompt',titleField:'Title',body:'Body',hook:'Hook',cta:'CTA',hashtags:'Hashtags',notChecked:'Not checked',completePulse:'Complete Brand Pulse to unlock brand rules.',readOnly:'Published drafts are read-only.',selectWarn:'Save or discard your unsaved changes before opening another draft.',scheduleApproved:'Approve this draft before scheduling it.',future:'Choose a future date and time.',emptySearch:'No drafts match this search.',retry:'Retry'},
 fa:{title:'استودیوی محتوا',sub:'یک بریف واقعی و پالس برند را به پیش‌نویس آماده بررسی و انتشار تبدیل کنید.',none:'هنوز پیش‌نویسی انتخاب نشده است.',generate:'تولید پیش‌نویس',blank:'پیش‌نویس خالی جدید',save:'ذخیره',unsaved:'تغییرات ذخیره نشده',saved:'ذخیره شد',brief:'بریف',rules:'قوانین برند',preview:'پیش‌نمایش پلتفرم',missing:'نیازمندی‌های ناقص راه‌اندازی',compliance:'بررسی انطباق',approval:'ارسال برای تأیید',schedule:'زمان‌بندی',export:'خروجی بسته کمکی',archive:'آرشیو',recent:'پیش‌نویس‌های اخیر',search:'جست‌وجوی پیش‌نویس‌ها',goal:'هدف',channel:'کانال',language:'زبان',type:'نوع محتوا',offer:'محصول / پیشنهاد',tone:'لحن',prompt:'دستور تولید',titleField:'عنوان',body:'متن',hook:'قلاب',cta:'دعوت به اقدام',hashtags:'هشتگ‌ها',notChecked:'بررسی نشده',completePulse:'برای فعال‌شدن قوانین برند، پالس برند را کامل کنید.',readOnly:'پیش‌نویس منتشرشده قابل ویرایش نیست.',selectWarn:'قبل از بازکردن پیش‌نویس دیگر، تغییرات را ذخیره یا لغو کنید.',scheduleApproved:'قبل از زمان‌بندی، پیش‌نویس را تأیید کنید.',future:'تاریخ و زمان آینده را انتخاب کنید.',emptySearch:'پیش‌نویسی با این جست‌وجو پیدا نشد.',retry:'تلاش دوباره'},
 de:{title:'Content Studio',sub:'Verwandeln Sie ein echtes Briefing und Brand Pulse in einen prüfbaren, plattformfertigen Entwurf.',none:'Noch kein Entwurf ausgewählt.',generate:'Entwurf generieren',blank:'Neuer leerer Entwurf',save:'Speichern',unsaved:'Ungespeicherte Änderungen',saved:'Gespeichert',brief:'Briefing',rules:'Markenregeln',preview:'Plattformvorschau',missing:'Fehlende Einrichtung',compliance:'Compliance prüfen',approval:'Zur Freigabe senden',schedule:'Planen',export:'Assisted Kit exportieren',archive:'Archivieren',recent:'Letzte Entwürfe',search:'Entwürfe suchen',goal:'Ziel',channel:'Kanal',language:'Sprache',type:'Content-Typ',offer:'Produkt / Angebot',tone:'Ton',prompt:'Generierungsanweisung',titleField:'Titel',body:'Text',hook:'Hook',cta:'CTA',hashtags:'Hashtags',notChecked:'Nicht geprüft',completePulse:'Vervollständigen Sie Brand Pulse, um Markenregeln zu aktivieren.',readOnly:'Veröffentlichte Entwürfe sind schreibgeschützt.',selectWarn:'Speichern oder verwerfen Sie Änderungen, bevor Sie einen anderen Entwurf öffnen.',scheduleApproved:'Geben Sie den Entwurf vor der Planung frei.',future:'Wählen Sie ein zukünftiges Datum und eine Uhrzeit.',emptySearch:'Keine Entwürfe entsprechen der Suche.',retry:'Erneut versuchen'}
};

export default function Page({params}:{params:Promise<{locale:string}>}) {
  const {locale}=use(params);
  return <AppShell locale={locale}><Studio locale={locale}/></AppShell>;
}

function Studio({locale}:{locale:string}) {
  const c=copies[locale]||copies.en;
  const toast=useToast();
  const searchParams=useSearchParams();
  const router=useRouter();
  const [overview,setOverview]=useState<StudioOverview|null>(null);
  const [draft,setDraft]=useState<StudioDraft>(blankDraft(locale));
  const [dirty,setDirty]=useState(false);
  const [initialLoading,setInitialLoading]=useState(true);
  const [busy,setBusy]=useState('');
  const [error,setError]=useState('');
  const [kit,setKit]=useState('');
  const [scheduleOpen,setScheduleOpen]=useState(false);
  const [query,setQuery]=useState('');
  const dir=draft.language==='fa'||locale==='fa'?'rtl':'ltr';
  const readOnly=draft.status==='published';

  useEffect(()=>{load(true)},[]);
  useEffect(()=>{
    const handler=(event:BeforeUnloadEvent)=>{if(dirty){event.preventDefault();event.returnValue=''}};
    const key=(event:KeyboardEvent)=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();save()}};
    window.addEventListener('beforeunload',handler);window.addEventListener('keydown',key);
    return()=>{window.removeEventListener('beforeunload',handler);window.removeEventListener('keydown',key)};
  },[dirty,draft]);

  async function load(first=false,preferredId?:number|string) {
    if(first)setInitialLoading(true);
    setError('');
    try{
      const data=await api.get<StudioOverview>('/studio/overview');
      setOverview(data);
      const requested=preferredId||searchParams.get('draft');
      const forceNew=searchParams.get('new')==='1';
      if(forceNew){setDraft(blankDraft(data.brand?.primary_language||locale));setDirty(false)}
      else if(requested){
        const found=data.drafts.find(x=>String(x.id)===String(requested));
        setDraft(found||await api.get<StudioDraft>(`/studio/drafts/${requested}`));setDirty(false);
      } else if(!draft.id&&data.drafts[0]){setDraft(data.drafts[0]);setDirty(false)}
    }catch(e:any){setError(e?.message||String(e))}
    finally{if(first)setInitialLoading(false)}
  }

  function update(key:keyof StudioDraft,value:any){if(readOnly)return toast(c.readOnly);setDraft(current=>({...current,[key]:value}));setDirty(true)}
  function payload(){return {title:draft.title,body:draft.body,hook:draft.hook,cta:draft.cta,hashtags:draft.hashtags,goal:draft.goal,channel:draft.channel,language:draft.language,content_type:draft.content_type,product_or_offer:draft.product_or_offer,tone:draft.tone,prompt:draft.prompt,status:draft.status}}
  function openDraft(next:StudioDraft){if(dirty&&!confirm(c.selectWarn))return;setDraft(next);setDirty(false);setError('');router.replace(`/${locale}/app/content-studio?draft=${next.id}`)}
  function newDraft(){if(dirty&&!confirm(c.selectWarn))return;setDraft(blankDraft(overview?.brand?.primary_language||locale));setDirty(true);router.replace(`/${locale}/app/content-studio?new=1`)}

  async function save(){
    if(readOnly)return toast(c.readOnly);
    setBusy('save');setError('');
    try{
      const result=draft.id?await api.patch<StudioDraft>(`/studio/drafts/${draft.id}`,payload()):await api.post<StudioDraft>('/studio/drafts',payload());
      setDraft(result);setDirty(false);toast(c.saved);router.replace(`/${locale}/app/content-studio?draft=${result.id}`);await load(false,result.id);return result;
    }catch(e:any){setError(e?.message||String(e));toast(e?.message||'Save failed')}
    finally{setBusy('')}
  }

  async function generate(){
    if(!overview?.setup.can_generate){toast(c.missing);return}
    if(!draft.goal?.trim()||!draft.channel||!draft.prompt?.trim()){toast(locale==='fa'?'هدف، کانال و دستور تولید الزامی است.':'Goal, channel and prompt are required.');return}
    setBusy('generate');setError('');
    try{
      const result=await api.post<{draft:StudioDraft;provider:string}>('/studio/generate',payload());
      setDraft(result.draft);setDirty(false);toast(`Generated · ${result.provider}`);router.replace(`/${locale}/app/content-studio?draft=${result.draft.id}`);await load(false,result.draft.id);
    }catch(e:any){setError(e?.message||String(e));toast(e?.message||'Generation failed')}
    finally{setBusy('')}
  }

  async function ensureSaved(){if(draft.id&&!dirty)return draft;return await save()}
  async function transform(action:string,target_language?:string){
    const saved=await ensureSaved();if(!saved)return;
    setBusy(action);setError('');
    try{const result=await api.post<StudioDraft>(`/studio/drafts/${saved.id}/transform`,{action,target_language});setDraft(result);setDirty(false);toast('Draft updated');await load(false,result.id)}catch(e:any){setError(e?.message||String(e));toast(e?.message||'Transform failed')}finally{setBusy('')}
  }
  async function check(){
    const saved=await ensureSaved();if(!saved)return;
    setBusy('check');setError('');
    try{const result=await api.post<any>(`/studio/drafts/${saved.id}/compliance-check`,{});setDraft(result.draft);toast(statusLabel(locale,result.compliance_result.status));await load(false,saved.id)}catch(e:any){setError(e?.message||String(e));toast(e?.message||'Compliance check failed')}finally{setBusy('')}
  }
  async function sendApproval(){
    const saved=await ensureSaved();if(!saved)return;
    setBusy('approval');setError('');
    try{const result=await api.post<any>(`/studio/drafts/${saved.id}/send-for-approval`,{});setDraft(result.draft);toast(`Approval #${result.approval_request_id}`);await load(false,saved.id)}catch(e:any){setError(e?.message||String(e));toast(e?.message||'Connect an approval method before sending.')}finally{setBusy('')}
  }
  async function schedule(event:any){
    event.preventDefault();
    const saved=await ensureSaved();if(!saved)return;
    if(saved.status!=='approved'){toast(c.scheduleApproved);return}
    const data=new FormData(event.currentTarget);const date=String(data.get('date')||'');const time=String(data.get('time')||'');
    if(new Date(`${date}T${time}`).getTime()<=Date.now()){toast(c.future);return}
    setBusy('schedule');setError('');
    try{const result=await api.post<any>(`/studio/drafts/${saved.id}/schedule`,{date,time,timezone:data.get('timezone'),channel:saved.channel});setDraft(result.draft);setScheduleOpen(false);toast(result.warning||'Scheduled');await load(false,saved.id)}catch(e:any){setError(e?.message||String(e));toast(e?.message||'Scheduling failed')}finally{setBusy('')}
  }
  async function exportKit(){const saved=await ensureSaved();if(!saved)return;setBusy('export');try{const result=await api.post<any>(`/studio/drafts/${saved.id}/export-assisted-kit`,{});setKit(result.content||'')}catch(e:any){toast(e?.message||'Export failed')}finally{setBusy('')}}
  async function archive(){if(!draft.id||!confirm(locale==='fa'?'این پیش‌نویس آرشیو شود؟':'Archive this draft?'))return;setBusy('archive');try{await api.delete(`/studio/drafts/${draft.id}`);toast(c.archive);setDraft(blankDraft(overview?.brand?.primary_language||locale));setDirty(false);router.replace(`/${locale}/app/content-studio`);await load()}catch(e:any){toast(e?.message||String(e))}finally{setBusy('')}}

  const channelOptions=Array.from(new Set([...(overview?.channels||[]),'instagram','telegram','bale','linkedin','google_business','email','blog']));
  const filteredDrafts=useMemo(()=>overview?.drafts.filter(x=>`${x.title} ${x.body} ${x.channel} ${x.status}`.toLowerCase().includes(query.toLowerCase()))||[],[overview,query]);
  const maxLength=draft.channel==='instagram'?2200:draft.channel==='linkedin'?3000:draft.channel==='telegram'||draft.channel==='bale'?4096:null;

  if(initialLoading)return <div className="grid gap-5 xl:grid-cols-[22rem_1fr_24rem]"><div className="panel h-[42rem] animate-pulse"/><div className="panel h-[42rem] animate-pulse"/><div className="panel h-[42rem] animate-pulse"/></div>;

  return <div className="space-y-5">
    <section className="command-card p-6"><div className="flex flex-wrap items-end gap-3"><div><p className="badge">{overview?.organization?.name||'Smarbiz'} · {overview?.brand?.name||'No brand'}</p><h1 className="mt-3 text-4xl font-black md:text-5xl">{c.title}</h1><p className="muted mt-2 max-w-3xl">{c.sub}</p></div><div className="ms-auto flex flex-wrap gap-2"><span className={dirty?'badge badge-warn':'badge badge-success'}>{dirty?c.unsaved:c.saved}</span><button className="chip" onClick={newDraft}>{c.blank}</button><button className="btn" disabled={!!busy||readOnly} onClick={save}>{busy==='save'?'…':c.save}</button></div></div></section>
    {error&&<div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"><span>{error}</span><button className="chip ms-3" onClick={()=>load()}>{c.retry}</button></div>}
    {!!overview?.setup.missing_requirements.length&&<div className="panel border-amber-200 bg-amber-50 p-4"><b>{c.missing}</b><div className="mt-2 flex flex-wrap gap-2">{overview.setup.missing_requirements.map(item=><a className="chip" href={`/${locale}${item.action_href}`} key={item.id}>{item.title}</a>)}</div></div>}

    <div className="grid gap-5 xl:grid-cols-[22rem_minmax(0,1fr)_24rem]">
      <aside className="panel h-fit p-5 xl:sticky xl:top-24"><div className="flex items-center"><h2 className="text-xl font-black">{c.brief}</h2><button className="chip ms-auto !py-1" onClick={newDraft}>＋</button></div><div className="mt-4 space-y-3"><Field label={c.goal} value={draft.goal} disabled={readOnly} onChange={(v:string)=>update('goal',v)}/><Select label={c.channel} value={draft.channel} disabled={readOnly} options={channelOptions} onChange={(v:string)=>update('channel',v)}/><Select label={c.language} value={draft.language} disabled={readOnly} options={['en','fa','de']} onChange={(v:string)=>update('language',v)}/><Select label={c.type} value={draft.content_type} disabled={readOnly} options={['post','reel','story','carousel','email','blog','google_update','telegram_post','bale_post']} onChange={(v:string)=>update('content_type',v)}/><Field label={c.offer} value={draft.product_or_offer} disabled={readOnly} list={overview?.products} onChange={(v:string)=>update('product_or_offer',v)}/><Field label={c.tone} value={draft.tone} disabled={readOnly} onChange={(v:string)=>update('tone',v)}/><TextArea label={c.prompt} value={draft.prompt} disabled={readOnly} onChange={(v:string)=>update('prompt',v)}/></div><button disabled={!!busy||readOnly||!overview?.setup.can_generate} className="btn mt-4 w-full disabled:cursor-not-allowed disabled:opacity-50" onClick={generate}>{busy==='generate'?'Generating…':c.generate}</button><div className="mt-6 border-t border-slate-200 pt-5"><b>{c.recent}</b><input className="field my-3" value={query} onChange={e=>setQuery(e.target.value)} placeholder={c.search}/><div className="max-h-72 space-y-2 overflow-auto">{filteredDrafts.length?filteredDrafts.map(item=><button className={`w-full rounded-xl border p-3 text-start ${String(item.id)===String(draft.id)?'border-blue-300 bg-blue-50':'border-slate-200 bg-white hover:bg-slate-50'}`} onClick={()=>openDraft(item)} key={item.id}><b className="block truncate">{item.title||'Untitled'}</b><div className="mt-1 flex items-center justify-between gap-2"><span className="muted text-xs">{item.channel}</span><span className="badge">{statusLabel(locale,item.status)}</span></div></button>):<p className="muted rounded-xl bg-slate-50 p-3 text-sm">{c.emptySearch}</p>}</div></div></aside>

      <section className="panel min-w-0 p-5" dir={dir}>{!draft.id&&!dirty&&!draft.body?<div className="grid min-h-[34rem] place-items-center text-center"><div><div className="mx-auto grid h-16 w-16 place-items-center rounded-3xl bg-blue-50 text-3xl">✍️</div><h2 className="mt-5 text-2xl font-black">{c.none}</h2><p className="muted mt-2">{c.sub}</p><button className="btn mt-4" onClick={()=>document.getElementById('studio-prompt')?.focus()}>{c.generate}</button></div></div>:<><input className="field text-xl font-black" disabled={readOnly} placeholder={c.titleField} value={draft.title} onChange={e=>update('title',e.target.value)}/><textarea className="field mt-4 min-h-80 text-base leading-7" disabled={readOnly} placeholder={c.body} value={draft.body} onChange={e=>update('body',e.target.value)}/><div className="muted mt-2 flex flex-wrap justify-between gap-2 text-xs"><span>{draft.body.length}{maxLength?` / ${maxLength}`:''} characters</span><span>{draft.updated_at?new Date(draft.updated_at).toLocaleString(locale):'Not saved'} · <b>{statusLabel(locale,draft.status)}</b></span></div><div className="mt-4 grid gap-3 md:grid-cols-3"><Field label={c.hook} value={draft.hook} disabled={readOnly} onChange={(v:string)=>update('hook',v)}/><Field label={c.cta} value={draft.cta} disabled={readOnly} onChange={(v:string)=>update('cta',v)}/><Field label={c.hashtags} value={draft.hashtags} disabled={readOnly} onChange={(v:string)=>update('hashtags',v)}/></div><div className="mt-5 flex flex-wrap gap-2">{[['rewrite','Rewrite'],['shorten','Shorten'],['more_formal','More formal'],['more_direct','More direct']].map(([action,label])=><button className="chip" disabled={!!busy||readOnly} onClick={()=>transform(action)} key={action}>{busy===action?'…':label}</button>)}<select className="chip" disabled={!!busy||readOnly} defaultValue="" onChange={e=>{if(e.target.value)transform('translate',e.target.value);e.target.value=''}}><option value="">Translate…</option><option value="en">English</option><option value="fa">Persian</option><option value="de">German</option></select><button className="chip" disabled={!!busy} onClick={check}>{busy==='check'?'…':c.compliance}</button><button className="chip" disabled={!!busy||readOnly||draft.status==='in_review'} onClick={sendApproval}>{busy==='approval'?'…':c.approval}</button><button className="chip" disabled={!!busy||readOnly} onClick={()=>draft.status==='approved'?setScheduleOpen(true):toast(c.scheduleApproved)}>{c.schedule}</button><button className="chip" disabled={!!busy} onClick={exportKit}>{c.export}</button>{draft.id&&draft.status!=='published'&&<button className="chip border-red-200 !text-red-700" disabled={!!busy} onClick={archive}>{c.archive}</button>}</div>{readOnly&&<p className="mt-4 rounded-2xl bg-slate-50 p-3 text-sm">{c.readOnly}</p>}</>}</section>

      <aside className="space-y-5"><div className="panel p-5"><h2 className="font-black">{c.rules}</h2>{overview?.brand_rules.length?overview.brand_rules.map(rule=><div className={`mt-3 rounded-xl p-3 text-sm ${rule.severity==='danger'?'bg-red-50 text-red-800':rule.severity==='warning'?'bg-amber-50 text-amber-900':'bg-slate-50'}`} key={rule.id}><b>{rule.label}</b><p className="mt-1">{rule.description}</p></div>):<p className="muted mt-3">{c.completePulse}</p>}<h3 className="mt-5 font-black">Compliance</h3><span className={`mt-2 ${draft.compliance_result?.status==='passed'?'badge badge-success':draft.compliance_result?.status==='blocked'?'badge border-red-200 bg-red-50 !text-red-700':'badge badge-warn'}`}>{statusLabel(locale,draft.compliance_result?.status||c.notChecked)}</span>{(draft.compliance_result?.warnings||draft.warnings||[]).map((warning:any,index:number)=><p className="mt-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800" key={warning.id||index}><b>{warning.title||'Warning'}</b><br/>{warning.description||warning.message||String(warning)}</p>)}</div><div className="panel p-5" dir={dir}><div className="flex items-center justify-between"><h2 className="font-black">{c.preview}</h2><span className="badge">{draft.channel}</span></div><div className="mt-3 overflow-hidden rounded-2xl border border-slate-200 bg-white"><div className="flex items-center gap-3 border-b border-slate-200 p-3"><div className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-blue-600 to-cyan-400 font-black text-white">{overview?.brand?.name?.slice(0,1)||'S'}</div><div><b className="text-sm">{overview?.brand?.name||'Brand'}</b><p className="muted text-xs">Preview · {draft.channel}</p></div></div><div className="whitespace-pre-wrap p-4 text-sm leading-6"><b>{draft.title||c.titleField}</b>{draft.hook&&<p className="mt-3 font-semibold">{draft.hook}</p>}<p className="mt-3">{draft.body||c.body}</p>{draft.cta&&<p className="mt-3 font-semibold">{draft.cta}</p>}{draft.hashtags&&<p className="mt-3 text-blue-700">{draft.hashtags}</p>}</div></div></div><HelpAside locale={locale} page="Content Studio"/></aside>
    </div>

    {scheduleOpen&&<Modal title={c.schedule} onClose={()=>setScheduleOpen(false)}><form onSubmit={schedule} className="space-y-3"><input className="field" name="date" type="date" min={new Date().toISOString().slice(0,10)} required/><input className="field" name="time" type="time" required/><input className="field" name="timezone" defaultValue={Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC'} required/><button className="btn w-full" disabled={busy==='schedule'}>{busy==='schedule'?'…':c.schedule}</button></form></Modal>}
    {kit&&<Modal title={c.export} onClose={()=>setKit('')}><textarea className="field min-h-80" value={kit} readOnly/><button className="btn mt-3" onClick={async()=>{await navigator.clipboard.writeText(kit);toast('Copied')}}>Copy all</button></Modal>}
  </div>;
}

function Field({label,value,onChange,list,disabled}:any){const id=`field-${String(label).replace(/\s/g,'-')}`;return <label className="block"><b className="text-sm">{label}</b>{list?.length?<><input className="field mt-1" disabled={disabled} list={id} value={value||''} onChange={e=>onChange(e.target.value)}/><datalist id={id}>{list.map((x:string)=><option key={x}>{x}</option>)}</datalist></>:<input className="field mt-1" disabled={disabled} value={value||''} onChange={e=>onChange(e.target.value)}/>}</label>}
function TextArea({label,value,onChange,disabled}:any){return <label className="block"><b className="text-sm">{label}</b><textarea id="studio-prompt" className="field mt-1 min-h-28" disabled={disabled} value={value||''} onChange={e=>onChange(e.target.value)}/></label>}
function Select({label,value,onChange,options,disabled}:any){return <label className="block"><b className="text-sm">{label}</b><select className="field mt-1" disabled={disabled} value={value||''} onChange={e=>onChange(e.target.value)}>{options.map((x:string)=><option key={x} value={x}>{x.replaceAll('_',' ')}</option>)}</select></label>}
function Modal({title,onClose,children}:any){return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-900/35 p-4" onClick={onClose}><div className="panel w-full max-w-xl p-5" onClick={e=>e.stopPropagation()}><div className="mb-4 flex items-center justify-between"><b>{title}</b><button className="chip" onClick={onClose}>×</button></div>{children}</div></div>}
