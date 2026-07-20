'use client';

import {use, useEffect, useMemo, useState} from 'react';
import Link from 'next/link';
import {AppShell} from '@/components/app-shell';
import {HelpAside} from '@/components/product-guidance';
import {useToast} from '@/components/ui/toast';
import {api} from '@/lib/api';
import {statusLabel, t} from '@/lib/i18n';

type Status = 'pending' | 'changes_requested' | 'approved' | 'rejected' | 'expired' | 'cancelled';
type Summary = {id:number|string;title:string;channel?:string;content_type?:string;status:Status;reviewer?:string|null;due_at?:string|null;updated_at?:string;href:string};
type Detail = Summary & {
  draft?: {id:number|string;title:string;body:string;hook?:string;cta?:string;hashtags?:string;status?:string;quality_score?:number|null;warnings?:any[]} | null;
  calendar_item?: {id:number|string;scheduled_at?:string|null} | null;
  public_url?: string|null;
  message?: string|null;
  actions: {id:number|string;action:string;actor_name?:string|null;comment?:string|null;created_at:string}[];
};
type Overview = {
  user:{id:number;name:string;email:string};organization:{id:number;name:string}|null;brand:{id:number;name:string;primary_language?:string}|null;
  summary:any;requests:Summary[];selected_request?:Detail|null;recommended_action:any;alerts:any[];
  channels:{telegram_connected:boolean;bale_connected:boolean;public_link_enabled:boolean};
};
type CreateForm = {
  draft_id:string; reviewer_name:string; reviewer_email:string; reviewer_phone:string;
  message:string; due_at:string; method:'public_link'|'telegram'|'bale'|'internal';
};

const emptyCreate:CreateForm = {draft_id:'',reviewer_name:'',reviewer_email:'',reviewer_phone:'',message:'',due_at:'',method:'public_link'};
const copy:any = {
  en:{title:'Approval review desk',sub:'Send real drafts for review, collect decisions, and preserve feedback before publishing.',create:'Create approval request',list:'Approval list',search:'Search approvals',empty:'No approval requests yet',emptySub:'Create the first request from a saved Studio draft.',select:'Select an approval request',actions:'Comments and actions',comment:'Add feedback or requested changes…',approve:'Approve',changes:'Request changes',reject:'Reject',memory:'Save feedback to Smarbiz Memory',copy:'Copy public link',history:'History',noComment:'No comment',filtered:'No requests match these filters.',connect:'Connect an approval method',connectSub:'Public links work immediately. Telegram and Bale require a configured connection.',retry:'Retry'},
  fa:{title:'میز بررسی و تأیید',sub:'پیش‌نویس‌های واقعی را برای بررسی بفرستید، تصمیم‌ها را ثبت کنید و بازخورد را پیش از انتشار نگه دارید.',create:'ساخت درخواست تأیید',list:'فهرست درخواست‌ها',search:'جست‌وجوی درخواست‌ها',empty:'هنوز درخواست تأییدی وجود ندارد',emptySub:'اولین درخواست را از یک پیش‌نویس ذخیره‌شده در استودیو بسازید.',select:'یک درخواست را انتخاب کنید',actions:'نظر و عملیات',comment:'بازخورد یا تغییرات درخواستی را بنویسید…',approve:'تأیید',changes:'درخواست تغییر',reject:'رد',memory:'ذخیره بازخورد در حافظه اسماربیز',copy:'کپی لینک عمومی',history:'تاریخچه',noComment:'بدون توضیح',filtered:'هیچ درخواستی با این فیلترها پیدا نشد.',connect:'اتصال روش تأیید',connectSub:'لینک عمومی فوراً کار می‌کند. تلگرام و بله به اتصال معتبر نیاز دارند.',retry:'تلاش دوباره'},
  de:{title:'Freigabe-Desk',sub:'Senden Sie echte Entwürfe zur Prüfung, erfassen Sie Entscheidungen und speichern Sie Feedback vor der Veröffentlichung.',create:'Freigabeanfrage erstellen',list:'Freigabeliste',search:'Freigaben suchen',empty:'Noch keine Freigabeanfragen',emptySub:'Erstellen Sie die erste Anfrage aus einem gespeicherten Studio-Entwurf.',select:'Freigabeanfrage auswählen',actions:'Kommentare und Aktionen',comment:'Feedback oder gewünschte Änderungen hinzufügen…',approve:'Freigeben',changes:'Änderungen anfordern',reject:'Ablehnen',memory:'Feedback im Smarbiz-Gedächtnis speichern',copy:'Öffentlichen Link kopieren',history:'Verlauf',noComment:'Kein Kommentar',filtered:'Keine Anfragen entsprechen diesen Filtern.',connect:'Freigabemethode verbinden',connectSub:'Öffentliche Links funktionieren sofort. Telegram und Bale benötigen eine konfigurierte Verbindung.',retry:'Erneut versuchen'}
};

export default function Page({params}:{params:Promise<{locale:string}>}) {
  const {locale} = use(params);
  return <AppShell locale={locale}><Approvals locale={locale}/></AppShell>;
}

function badge(status?:string) {
  if (status === 'approved') return 'badge badge-success';
  if (status === 'rejected' || status === 'expired' || status === 'cancelled') return 'badge border-red-200 bg-red-50 !text-red-700';
  if (status === 'changes_requested') return 'badge badge-warn';
  return 'badge';
}

function Approvals({locale}:{locale:string}) {
  const d = t(locale);
  const c = copy[locale] || copy.en;
  const toast = useToast();
  const [overview, setOverview] = useState<Overview|null>(null);
  const [selected, setSelected] = useState<Detail|null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('all');
  const [channel, setChannel] = useState('all');
  const [sort, setSort] = useState('newest');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<CreateForm>(emptyCreate);

  async function load(preferredId?:number|string) {
    setLoading(true);
    try {
      const o = await api.get<Overview>('/approvals/overview');
      setOverview(o);
      setErr('');
      const id = preferredId || selected?.id || o.selected_request?.id || o.requests[0]?.id;
      if (id) {
        try { setSelected(await api.get<Detail>(`/approvals/requests/${id}`)); }
        catch { setSelected(o.selected_request || null); }
      } else setSelected(null);
    } catch (e:any) {
      setErr(e?.message || 'Could not load approvals');
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    let rows = [...(overview?.requests || [])].filter(x =>
      (status === 'all' || x.status === status) &&
      (channel === 'all' || x.channel === channel) &&
      `${x.title} ${x.status} ${x.channel} ${x.reviewer || ''}`.toLowerCase().includes(q.toLowerCase())
    );
    if (sort === 'due') rows.sort((a,b) => (a.due_at || '9999').localeCompare(b.due_at || '9999'));
    else if (sort === 'status') rows.sort((a,b) => a.status.localeCompare(b.status));
    else rows.sort((a,b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
    return rows;
  }, [overview, q, status, channel, sort]);

  async function open(id:any) {
    try { setSelected(await api.get<Detail>(`/approvals/requests/${id}`)); }
    catch (e:any) { toast(e?.message || String(e)); }
  }

  async function act(kind:'approve'|'request-changes'|'reject') {
    if (!selected) return;
    if ((kind === 'request-changes' || kind === 'reject') && !comment.trim()) {
      toast(locale === 'fa' ? 'برای این عملیات توضیح لازم است.' : 'A comment is required for this action.');
      return;
    }
    if (kind === 'reject' && !confirm(locale === 'fa' ? 'این درخواست رد شود؟' : 'Reject this approval request?')) return;
    setBusy(kind);
    try {
      const result = await api.post<Detail>(`/approvals/requests/${selected.id}/${kind}`, {comment: comment.trim() || null});
      setSelected(result);
      setComment('');
      toast(kind === 'approve' ? c.approve : kind === 'reject' ? c.reject : c.changes);
      await load(selected.id);
    } catch (e:any) { toast(e?.message || String(e)); }
    finally { setBusy(''); }
  }

  async function util(kind:'memory'|'copy'|'telegram'|'bale') {
    if (!selected) return;
    setBusy(kind);
    const path = kind === 'memory' ? 'save-feedback-to-memory' : kind === 'copy' ? 'copy-link-event' : kind === 'telegram' ? 'send-via-telegram' : 'send-via-bale';
    try {
      const result = await api.post<any>(`/approvals/requests/${selected.id}/${path}`, {comment: comment.trim() || null});
      if (kind === 'copy') {
        const raw = result.public_url || selected.public_url;
        if (!raw) throw new Error('Public link is not available for this request.');
        const url = raw.startsWith('http') ? raw : `${location.origin}/${locale}${raw.startsWith('/') ? raw : `/${raw}`}`;
        await navigator.clipboard.writeText(url);
        toast(c.copy);
      } else toast(result.message || 'Done');
      await load(selected.id);
    } catch (e:any) { toast(e?.message || String(e)); }
    finally { setBusy(''); }
  }

  if (loading && !overview) return <div className="space-y-4"><div className="h-10 w-72 animate-pulse rounded-xl bg-slate-200"/><div className="grid gap-5 xl:grid-cols-3"><div className="panel h-72 animate-pulse"/><div className="panel h-72 animate-pulse"/><div className="panel h-72 animate-pulse"/></div></div>;
  if (err && !overview) return <div className="panel p-6"><h1 className="text-2xl font-black">{c.title}</h1><p className="muted mt-2">{err}</p><button className="btn mt-4" onClick={() => load()}>{c.retry}</button></div>;

  const closed = selected && ['approved','rejected','expired','cancelled'].includes(selected.status);
  const availableChannels = [...new Set((overview?.requests || []).map(x => x.channel).filter(Boolean))] as string[];

  return <div className="space-y-5">
    <section className="command-card p-6"><div className="flex flex-wrap items-start gap-3"><div><p className="badge">{overview?.organization?.name || d.common.organization} · {overview?.brand?.name || ''}</p><h1 className="mt-3 text-4xl font-black md:text-5xl">{c.title}</h1><p className="muted mt-2 max-w-3xl">{c.sub}</p></div><button className="btn ms-auto" onClick={() => {setForm(emptyCreate);setCreateOpen(true)}}>{c.create}</button></div></section>

    {overview && !overview.channels.telegram_connected && !overview.channels.bale_connected && <div className="panel border-amber-200 bg-amber-50 p-4 text-amber-900"><b>{c.connect}</b><p className="text-sm">{c.connectSub}</p><Link className="chip mt-2" href={`/${locale}/app/integrations`}>{c.connect}</Link></div>}

    {!overview?.requests.length
      ? <section className="panel p-8 text-center"><span className="badge">Approvals</span><h2 className="mt-4 text-3xl font-black">{c.empty}</h2><p className="muted mt-2">{c.emptySub}</p><div className="mt-5 flex flex-wrap justify-center gap-2"><button className="btn" onClick={() => setCreateOpen(true)}>{c.create}</button><Link className="chip" href={`/${locale}/app/content-studio`}>{d.actions.open}</Link></div></section>
      : <div className="grid gap-5 xl:grid-cols-[22rem_minmax(0,1fr)_22rem]">
        <aside className="panel h-fit p-4 xl:sticky xl:top-24"><h2 className="font-black">{c.list}</h2><input className="field mt-3" value={q} onChange={e => setQ(e.target.value)} placeholder={c.search}/><div className="mt-3 grid grid-cols-2 gap-2"><select className="field" value={status} onChange={e => setStatus(e.target.value)}><option value="all">All</option>{['pending','changes_requested','approved','rejected','expired','cancelled'].map(x => <option key={x} value={x}>{statusLabel(locale,x)}</option>)}</select><select className="field" value={channel} onChange={e => setChannel(e.target.value)}><option value="all">All channels</option>{availableChannels.map(x => <option key={x}>{x}</option>)}</select><select className="field col-span-2" value={sort} onChange={e => setSort(e.target.value)}><option value="newest">Newest</option><option value="due">Due soon</option><option value="status">Status</option></select></div><div className="mt-3 max-h-[60vh] space-y-2 overflow-auto">{filtered.length ? filtered.map(x => <button className={`block w-full rounded-xl border p-3 text-start transition ${selected?.id === x.id ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-white hover:bg-slate-50'}`} onClick={() => open(x.id)} key={x.id}><b className="line-clamp-2">{x.title}</b><p className="muted text-sm">{x.channel || 'No channel'} · {x.content_type || 'content'}</p><div className="mt-2 flex items-center justify-between gap-2"><span className={badge(x.status)}>{statusLabel(locale,x.status)}</span>{x.due_at && <span className="muted text-xs">{new Date(x.due_at).toLocaleDateString(locale)}</span>}</div></button>) : <p className="muted rounded-xl bg-slate-50 p-4 text-sm">{c.filtered}</p>}</div></aside>

        <section className="panel min-w-0 p-5 md:p-6"><span className={badge(selected?.status)}>{selected ? statusLabel(locale,selected.status) : c.select}</span><h2 className="mt-4 text-3xl font-black">{selected?.title || c.select}</h2>{selected?.reviewer && <p className="muted mt-1 text-sm">Reviewer: {selected.reviewer}</p>}
          {selected?.draft ? <div className="mt-5 space-y-4"><div className="flex flex-wrap gap-2"><span className="badge">{selected.channel}</span><span className="badge">{selected.content_type}</span><Link className="chip" href={`/${locale}/app/content-studio?draft=${selected.draft.id}`}>Related Studio draft</Link>{selected.calendar_item && <Link className="chip" href={`/${locale}/app/calendar?item=${selected.calendar_item.id}`}>Related Calendar item</Link>}</div><div className="rounded-2xl border border-slate-200 bg-slate-50 p-5" dir={selected.draft.body?.match(/[\u0600-\u06ff]/) ? 'rtl' : 'auto'}><b>{selected.draft.title}</b>{selected.draft.hook && <p className="mt-3"><b>Hook:</b> {selected.draft.hook}</p>}<p className="mt-3 whitespace-pre-wrap">{selected.draft.body}</p>{selected.draft.cta && <p className="mt-3"><b>CTA:</b> {selected.draft.cta}</p>}{selected.draft.hashtags && <p className="mt-3 text-blue-700">{selected.draft.hashtags}</p>}</div><div className="rounded-2xl border border-slate-200 p-5"><b>Platform preview</b><p className="muted mt-1 text-sm">{platformPreview(selected.channel)}</p><p className="mt-3 whitespace-pre-wrap">{selected.draft.body}</p></div></div>
          : selected ? <div className="mt-6 rounded-2xl border border-slate-200 p-6"><b>This approval request has no linked draft.</b><p className="muted">Create a new request from Studio.</p><Link className="btn mt-4" href={`/${locale}/app/content-studio`}>Open Studio</Link></div> : null}
          <div className="mt-6"><h3 className="font-black">{c.history}</h3><div className="mt-2 space-y-2">{selected?.actions?.length ? selected.actions.map(a => <div className="rounded-xl bg-slate-50 p-3" key={a.id}><div className="flex items-center justify-between gap-2"><b>{statusLabel(locale,a.action)}</b><span className="muted text-xs">{a.created_at && new Date(a.created_at).toLocaleString(locale)}</span></div><p className="muted mt-1 text-sm">{a.comment || c.noComment}</p></div>) : <p className="muted rounded-xl bg-slate-50 p-3 text-sm">No actions yet.</p>}</div></div>
        </section>

        <aside className="space-y-5"><div className="panel p-5"><h2 className="font-black">{c.actions}</h2><textarea className="field mt-3 min-h-28" value={comment} onChange={e => setComment(e.target.value)} placeholder={c.comment}/><div className="mt-3 grid gap-2"><button disabled={!selected || !!closed || !!busy} className="btn disabled:cursor-not-allowed disabled:opacity-50" onClick={() => act('approve')}>{busy === 'approve' ? '…' : c.approve}</button><button disabled={!selected || !!closed || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => act('request-changes')}>{c.changes}</button><button disabled={!selected || !!closed || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => act('reject')}>{c.reject}</button><button disabled={!selected || !comment.trim() || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => util('memory')}>{c.memory}</button><button disabled={!selected || !overview?.channels.telegram_connected || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" title={!overview?.channels.telegram_connected ? 'Connect Telegram first' : ''} onClick={() => util('telegram')}>Send via Telegram</button><button disabled={!selected || !overview?.channels.bale_connected || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" title={!overview?.channels.bale_connected ? 'Connect Bale first' : ''} onClick={() => util('bale')}>Send via Bale</button><button disabled={!selected || !overview?.channels.public_link_enabled || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => util('copy')}>{c.copy}</button></div>{closed && <p className="muted mt-3 text-sm">This request is closed. Create a new revision to collect another decision.</p>}</div><div className="panel p-5"><h2 className="font-black">Next recommended action</h2><b className="mt-2 block">{overview?.recommended_action.title}</b><p className="muted text-sm">{overview?.recommended_action.description}</p><Link className="chip mt-3" href={`/${locale}${overview?.recommended_action.action_href || '/app/integrations'}`}>{overview?.recommended_action.action_label}</Link></div><HelpAside locale={locale} page="Approval review desk"/></aside>
      </div>}

    {createOpen && <CreateModal locale={locale} overview={overview} form={form} setForm={setForm} close={() => setCreateOpen(false)} done={async (result:any) => {setCreateOpen(false);setForm(emptyCreate);toast('Approval request created');await load(result.id)}}/>}
  </div>;
}

function CreateModal({locale, overview, form, setForm, close, done}:any) {
  const c = copy[locale] || copy.en;
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');
  useEffect(() => {api.get<any[]>('/studio/drafts').then(setDrafts).catch((e:any) => setErr(e?.message || String(e))).finally(() => setLoading(false))}, []);
  async function submit() {
    if (!form.draft_id) {setErr('Select a saved draft first.');return;}
    if (form.reviewer_email && !/^\S+@\S+\.\S+$/.test(form.reviewer_email)) {setErr('Enter a valid reviewer email.');return;}
    setSubmitting(true);setErr('');
    try {
      const payload = {
        draft_id:Number(form.draft_id),
        reviewer_name:form.reviewer_name.trim() || null,
        reviewer_email:form.reviewer_email.trim() || null,
        reviewer_phone:form.reviewer_phone.trim() || null,
        message:form.message.trim() || null,
        due_at:form.due_at ? new Date(form.due_at).toISOString() : null,
        method:form.method,
      };
      done(await api.post<Detail>('/approvals/requests', payload));
    } catch (e:any) {setErr(e?.message || String(e));}
    finally {setSubmitting(false);}
  }
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 p-4" onClick={close}><div className="panel max-h-[92vh] w-full max-w-2xl overflow-auto p-6" onClick={e => e.stopPropagation()}><div className="flex items-center gap-3"><div><h2 className="text-2xl font-black">{c.create}</h2><p className="muted text-sm">Choose a saved draft and optionally identify the reviewer.</p></div><button className="chip ms-auto" onClick={close}>×</button></div>{err && <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-700">{err}</p>}<div className="mt-5 space-y-4"><label className="block text-sm font-bold">Draft *<select className="field mt-2" disabled={loading} value={form.draft_id} onChange={e => setForm({...form,draft_id:e.target.value})}><option value="">{loading ? 'Loading drafts…' : 'Select a draft'}</option>{drafts.filter(x => !['published','archived'].includes(x.status)).map(x => <option value={x.id} key={x.id}>{x.title} · {x.channel} · {statusLabel(locale,x.status)}</option>)}</select></label>{!loading && !drafts.length && <div className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">No saved drafts are available. <Link className="font-bold underline" href={`/${locale}/app/content-studio?new=1`}>Create one in Studio.</Link></div>}<div className="grid gap-4 md:grid-cols-2"><Field label="Reviewer name" value={form.reviewer_name} onChange={(v:string) => setForm({...form,reviewer_name:v})}/><Field label="Reviewer email" type="email" value={form.reviewer_email} onChange={(v:string) => setForm({...form,reviewer_email:v})}/><Field label="Reviewer phone" type="tel" value={form.reviewer_phone} onChange={(v:string) => setForm({...form,reviewer_phone:v})}/><Field label="Due date" type="datetime-local" value={form.due_at} onChange={(v:string) => setForm({...form,due_at:v})}/></div><label className="block text-sm font-bold">Message<textarea className="field mt-2 min-h-24" value={form.message} onChange={e => setForm({...form,message:e.target.value})} placeholder="Context for the reviewer"/></label><label className="block text-sm font-bold">Delivery method<select className="field mt-2" value={form.method} onChange={e => setForm({...form,method:e.target.value})}><option value="public_link" disabled={!overview?.channels.public_link_enabled}>Public link</option><option value="telegram" disabled={!overview?.channels.telegram_connected}>Telegram{!overview?.channels.telegram_connected ? ' · not connected' : ''}</option><option value="bale" disabled={!overview?.channels.bale_connected}>Bale{!overview?.channels.bale_connected ? ' · not connected' : ''}</option><option value="internal">Internal only</option></select></label></div><div className="mt-6 flex flex-wrap justify-end gap-2"><button className="chip" onClick={close}>Cancel</button><button className="btn" disabled={submitting || !form.draft_id} onClick={submit}>{submitting ? 'Creating…' : c.create}</button></div></div></div>;
}

function platformPreview(channel?:string) {
  const value = channel?.toLowerCase() || '';
  if (value.includes('telegram') || value.includes('bale')) return 'Message preview';
  if (value.includes('linkedin')) return 'LinkedIn post preview';
  if (value.includes('google')) return 'Google Business update preview';
  if (value.includes('email')) return 'Email body preview';
  return 'Social caption preview';
}
function Field({label, value, onChange, type='text'}:any) {return <label className="block text-sm font-bold">{label}<input className="field mt-2" type={type} value={value || ''} onChange={e => onChange(e.target.value)}/></label>}
