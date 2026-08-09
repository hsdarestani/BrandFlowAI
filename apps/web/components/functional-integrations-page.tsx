'use client';

import {useEffect,useMemo,useState} from 'react';
import {api} from '@/lib/api';
import {useToast} from '@/components/ui/toast';

type Catalog={provider:string;label:string;category:string;purpose:string;status:string;is_available:boolean;is_assisted:boolean;connection_id:number|null;capabilities:Record<string,any>;setup_requirements?:string};
type Overview={catalog:Catalog[];summary:Record<string,number>;alerts:any[]};
type Connection={id:number;provider:string;display_name:string;status:string;config:Record<string,any>;last_test_status?:string;last_test_message?:string};

type Field={key:string;label:string;secret?:boolean;textarea?:boolean;placeholder?:string};
const fields:Record<string,Field[]>={
 telegram:[{key:'bot_token',label:'Bot token',secret:true},{key:'chat_id',label:'Default chat / channel ID'},{key:'webhook_secret',label:'Webhook secret',secret:true}],
 bale:[{key:'bot_token',label:'Bot token',secret:true},{key:'chat_id',label:'Default chat / channel ID'},{key:'webhook_secret',label:'Webhook secret',secret:true}],
 brevo:[{key:'api_key',label:'API key',secret:true},{key:'sender_email',label:'Verified sender email'},{key:'sender_name',label:'Sender name'},{key:'test_recipient_email',label:'Test recipient email'},{key:'approval_recipient_email',label:'Approval recipient email'}],
 woocommerce:[{key:'site_url',label:'Store URL',placeholder:'https://shop.example.com'},{key:'consumer_key',label:'Consumer key',secret:true},{key:'consumer_secret',label:'Consumer secret',secret:true}],
 ga4:[{key:'property_id',label:'GA4 property ID'},{key:'service_account_json',label:'Service-account JSON',secret:true,textarea:true}],
 approval_link:[],
};
const directProviders=new Set(Object.keys(fields));
const copy:any={
 fa:{title:'اتصال‌ها',sub:'فقط اتصال‌هایی که واقعاً API دارند به‌عنوان اتصال مستقیم نمایش داده می‌شوند. بقیه صریحاً «انتشار کمکی» هستند.',connected:'متصل',test:'تست زنده',save:'ذخیره تنظیمات',configure:'تنظیم',assisted:'فقط کمکی',direct:'مستقیم',close:'بستن',send:'ارسال تست',noFields:'این اتصال نیاز به credential ندارد.',saved:'تنظیمات ذخیره شد. برای فعال شدن، تست زنده را اجرا کنید.',assistedText:'OAuth/API مستقیم این سرویس در این استقرار فعال نیست؛ اسماربیز نتیجه جعلی برنمی‌گرداند و فقط workflow کمکی ارائه می‌دهد.',refresh:'بازخوانی'},
 de:{title:'Integrationen',sub:'Nur tatsächlich implementierte APIs werden als direkte Verbindungen angezeigt. Andere Dienste sind klar als assistierte Workflows markiert.',connected:'Verbunden',test:'Live testen',save:'Einstellungen speichern',configure:'Konfigurieren',assisted:'Nur assistiert',direct:'Direkt',close:'Schließen',send:'Test senden',noFields:'Für diese Verbindung sind keine Zugangsdaten nötig.',saved:'Einstellungen gespeichert. Führen Sie den Live-Test aus, um die Verbindung zu aktivieren.',assistedText:'Direktes OAuth/API ist in dieser Bereitstellung nicht aktiviert. Smarbiz meldet keinen falschen Erfolg und nutzt nur einen assistierten Workflow.',refresh:'Aktualisieren'},
 en:{title:'Integrations',sub:'Only APIs that are actually implemented are shown as direct connections. Everything else is explicitly assisted-only.',connected:'Connected',test:'Live test',save:'Save settings',configure:'Configure',assisted:'Assisted only',direct:'Direct',close:'Close',send:'Send test',noFields:'This connection requires no credentials.',saved:'Settings saved. Run a live test to activate the connection.',assistedText:'Direct OAuth/API is not enabled in this deployment. Smarbiz does not fake success and uses an assisted workflow only.',refresh:'Refresh'},
};

export function FunctionalIntegrationsPage({locale}:{locale:string}){
 const c=copy[locale]||copy.en;const toast=useToast();
 const [overview,setOverview]=useState<Overview|null>(null);const [connections,setConnections]=useState<Connection[]>([]);const [loading,setLoading]=useState(true);const [selected,setSelected]=useState<Catalog|null>(null);const [form,setForm]=useState<Record<string,string>>({});const [busy,setBusy]=useState('');
 async function load(){setLoading(true);try{const [o,cs]=await Promise.all([api.get<Overview>('/integrations/overview'),api.get<Connection[]>('/integrations/connections')]);setOverview(o);setConnections(cs)}catch(e:any){toast(e?.message||String(e))}finally{setLoading(false)}}
 useEffect(()=>{load()},[]);
 const conn=useMemo(()=>selected?connections.find(x=>x.provider===selected.provider):undefined,[connections,selected]);
 function open(item:Catalog){setSelected(item);const existing=connections.find(x=>x.provider===item.provider);setForm(Object.fromEntries((fields[item.provider]||[]).map(f=>[f.key,String(existing?.config?.[f.key]||'')])))}
 async function save(){if(!selected)return;setBusy('save');try{const payload={provider:selected.provider,display_name:selected.label,config:form};if(conn)await api.patch(`/integrations/connections/${conn.id}`,payload);else await api.post('/integrations/connections',payload);toast(c.saved);await load();setSelected(null)}catch(e:any){toast(e?.message||String(e))}finally{setBusy('')}}
 async function test(item:Catalog){const id=item.connection_id||connections.find(x=>x.provider===item.provider)?.id;if(!id){open(item);return}setBusy(`test-${item.provider}`);try{const r:any=await api.post(`/integrations/connections/${id}/test`,{});toast(r.message||'OK');await load()}catch(e:any){toast(e?.message||String(e));await load()}finally{setBusy('')}}
 async function sendTest(item:Catalog){const id=item.connection_id||connections.find(x=>x.provider===item.provider)?.id;if(!id)return;setBusy(`send-${item.provider}`);try{const r:any=await api.post(`/integrations/connections/${id}/send-test`,{});toast(r.message||r.status||'OK')}catch(e:any){toast(e?.message||String(e))}finally{setBusy('')}}
 if(loading&&!overview)return <div className="grid gap-4 md:grid-cols-3">{[1,2,3,4,5,6].map(i=><div key={i} className="card h-40 animate-pulse"/>)}</div>;
 return <div className="space-y-6">
  <section className="command-card p-6"><div className="flex flex-wrap items-start gap-3"><div><h1 className="text-4xl font-black">{c.title}</h1><p className="muted mt-2 max-w-4xl">{c.sub}</p></div><button className="chip ms-auto" onClick={load}>{c.refresh}</button></div><div className="mt-5 grid gap-3 sm:grid-cols-3"><K label={c.connected} value={overview?.summary?.connected_count||0}/><K label={c.direct} value={overview?.summary?.publishing_connected||0}/><K label={c.assisted} value={overview?.catalog?.filter(x=>x.is_assisted).length||0}/></div></section>
  {!!overview?.alerts?.length&&<div className="space-y-2">{overview.alerts.map((a:any)=><div key={a.id} className="rounded-2xl border border-amber-200 bg-amber-50 p-4"><b>{a.title}</b><p className="mt-1 text-sm">{a.description}</p></div>)}</div>}
  <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{overview?.catalog?.map(item=>{
   const direct=directProviders.has(item.provider);const current=connections.find(x=>x.provider===item.provider);const status=current?.status||item.status;
   return <article key={item.provider} className="card p-5"><div className="flex items-start gap-3"><div className="min-w-0 flex-1"><h2 className="text-xl font-black">{item.label}</h2><p className="muted mt-1 text-sm">{item.purpose}</p></div><span className={`badge ${status==='connected'?'!bg-emerald-50 !text-emerald-700':item.is_assisted?'!bg-amber-50 !text-amber-700':''}`}>{status==='connected'?c.connected:item.is_assisted?c.assisted:status}</span></div>
    <div className="mt-4 flex flex-wrap gap-2">{direct&&<button className="btn" onClick={()=>open(item)}>{c.configure}</button>}{direct&&current&&<button className="chip" disabled={busy===`test-${item.provider}`} onClick={()=>test(item)}>{c.test}</button>}{current&&['telegram','bale','brevo'].includes(item.provider)&&<button className="chip" disabled={busy===`send-${item.provider}`} onClick={()=>sendTest(item)}>{c.send}</button>}</div>
    {item.is_assisted&&<p className="mt-4 rounded-xl bg-slate-50 p-3 text-sm leading-6">{c.assistedText}</p>}
    {current?.last_test_message&&<p className="muted mt-3 text-xs">{current.last_test_message}</p>}
   </article>})}</section>
  {selected&&<div className="fixed inset-0 z-[90] grid place-items-center bg-slate-950/40 p-4" onMouseDown={e=>{if(e.target===e.currentTarget)setSelected(null)}}><div className="panel max-h-[88vh] w-full max-w-2xl overflow-auto p-6"><div className="flex items-start gap-3"><div><h2 className="text-2xl font-black">{selected.label}</h2><p className="muted mt-1 text-sm">{selected.setup_requirements}</p></div><button className="chip ms-auto" onClick={()=>setSelected(null)}>{c.close}</button></div>
   <div className="mt-5 space-y-4">{(fields[selected.provider]||[]).map(field=><label key={field.key} className="block text-sm font-bold">{field.label}{field.textarea?<textarea className="field mt-1 min-h-36 font-mono text-xs" value={form[field.key]||''} placeholder={field.placeholder} onChange={e=>setForm({...form,[field.key]:e.target.value})}/>:<input className="field mt-1" type={field.secret?'password':'text'} value={form[field.key]||''} placeholder={field.placeholder} onChange={e=>setForm({...form,[field.key]:e.target.value})}/>}</label>)}{!(fields[selected.provider]||[]).length&&<p className="rounded-xl bg-slate-50 p-4">{c.noFields}</p>}</div>
   <div className="mt-6 flex justify-end gap-2"><button className="chip" onClick={()=>setSelected(null)}>{c.close}</button><button className="btn" disabled={busy==='save'} onClick={save}>{c.save}</button></div>
  </div></div>}
 </div>
}
function K({label,value}:{label:string;value:any}){return <div className="rounded-2xl border bg-white p-4"><p className="muted text-xs font-bold">{label}</p><p className="mt-2 text-2xl font-black">{value}</p></div>}
