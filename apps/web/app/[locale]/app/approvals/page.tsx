'use client';

import {useEffect, useMemo, useState} from 'react';
import Link from 'next/link';
import {useParams} from 'next/navigation';
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
  user?:{id:number;name:string;email:string};organization?:{id:number;name:string}|null;brand?:{id:number;name:string;primary_language?:string}|null;
  summary?:any;requests:Summary[];selected_request?:Detail|null;recommended_action?:any;alerts?:any[];
  channels:{telegram_connected:boolean;bale_connected:boolean;public_link_enabled:boolean};
};
type CreateForm = {
  draft_id:string; reviewer_name:string; reviewer_email:string; reviewer_phone:string;
  message:string; due_at:string; method:'public_link'|'telegram'|'bale'|'internal';
};

type Locale = 'en'|'fa'|'de';

const emptyCreate:CreateForm = {draft_id:'',reviewer_name:'',reviewer_email:'',reviewer_phone:'',message:'',due_at:'',method:'public_link'};
const disconnectedChannels = {telegram_connected:false,bale_connected:false,public_link_enabled:true};

const copy:any = {
  en:{
    title:'Approval review desk',sub:'Send real drafts for review, collect decisions, and preserve feedback before publishing.',create:'Create approval request',list:'Approval list',search:'Search approvals',empty:'No approval requests yet',emptySub:'Create the first request from a saved Studio draft.',select:'Select an approval request',actions:'Comments and actions',comment:'Add feedback or requested changes…',approve:'Approve',changes:'Request changes',reject:'Reject',memory:'Save feedback to Smarbiz Memory',copy:'Copy public link',history:'History',noComment:'No comment',filtered:'No requests match these filters.',connect:'Connect an approval method',connectSub:'Public links work immediately. Telegram and Bale require a configured connection.',retry:'Retry',
    approvals:'Approvals',all:'All',allChannels:'All channels',newest:'Newest',dueSoon:'Due soon',statusSort:'Status',noChannel:'No channel',content:'content',reviewer:'Reviewer',relatedStudio:'Related Studio draft',relatedCalendar:'Related Calendar item',hook:'Hook',cta:'CTA',platformPreview:'Platform preview',noDraftTitle:'This approval request has no linked draft.',noDraftSub:'Create a new request from Studio.',openStudio:'Open Studio',noActions:'No actions yet.',connectTelegramFirst:'Connect Telegram first',connectBaleFirst:'Connect Bale first',sendTelegram:'Send via Telegram',sendBale:'Send via Bale',closed:'This request is closed. Create a new revision to collect another decision.',nextAction:'Next recommended action',recommendedTitle:'Continue setup',recommendedDesc:'Complete the next available step to keep the approval workflow moving.',continue:'Continue',
    modalSub:'Choose a saved draft and optionally identify the reviewer.',draft:'Draft',loadingDrafts:'Loading drafts…',selectDraft:'Select a draft',noDrafts:'No saved drafts are available.',createStudio:'Create one in Studio.',reviewerName:'Reviewer name',reviewerEmail:'Reviewer email',reviewerPhone:'Reviewer phone',dueDate:'Due date',message:'Message',messagePlaceholder:'Context for the reviewer',deliveryMethod:'Delivery method',publicLink:'Public link',notConnected:'not connected',internalOnly:'Internal only',cancel:'Cancel',creating:'Creating…',selectDraftError:'Select a saved draft first.',emailError:'Enter a valid reviewer email.',loadError:'Could not load approvals.',draftsLoadError:'Could not load saved drafts.',publicLinkUnavailable:'Public link is not available for this request.',commentRequired:'A comment is required for this action.',rejectConfirm:'Reject this approval request?',createdToast:'Approval request created',done:'Done',sent:'Sent',untitledDraft:'Untitled draft',
    previewMessage:'Message preview',previewLinkedIn:'LinkedIn post preview',previewGoogle:'Google Business update preview',previewEmail:'Email body preview',previewSocial:'Social caption preview',
    historyActions:{created:'Created',sent:'Sent',link_rotated:'Public link refreshed',feedback_saved:'Feedback saved',approved:'Approved',rejected:'Rejected',changes_requested:'Changes requested'}
  },
  fa:{
    title:'میز بررسی و تأیید',sub:'پیش‌نویس‌های واقعی را برای بررسی بفرستید، تصمیم‌ها را ثبت کنید و بازخورد را پیش از انتشار نگه دارید.',create:'ساخت درخواست تأیید',list:'فهرست درخواست‌ها',search:'جست‌وجوی درخواست‌ها',empty:'هنوز درخواست تأییدی وجود ندارد',emptySub:'اولین درخواست را از یک پیش‌نویس ذخیره‌شده در استودیو بسازید.',select:'یک درخواست را انتخاب کنید',actions:'نظر و عملیات',comment:'بازخورد یا تغییرات درخواستی را بنویسید…',approve:'تأیید',changes:'درخواست تغییر',reject:'رد',memory:'ذخیره بازخورد در حافظه اسماربیز',copy:'کپی لینک عمومی',history:'تاریخچه',noComment:'بدون توضیح',filtered:'هیچ درخواستی با این فیلترها پیدا نشد.',connect:'اتصال روش تأیید',connectSub:'لینک عمومی فوراً کار می‌کند. تلگرام و بله به اتصال معتبر نیاز دارند.',retry:'تلاش دوباره',
    approvals:'تأییدها',all:'همه',allChannels:'همه کانال‌ها',newest:'جدیدترین',dueSoon:'نزدیک‌ترین موعد',statusSort:'وضعیت',noChannel:'بدون کانال',content:'محتوا',reviewer:'بررسی‌کننده',relatedStudio:'پیش‌نویس مرتبط در استودیو',relatedCalendar:'آیتم مرتبط در تقویم',hook:'شروع محتوا',cta:'دعوت به اقدام',platformPreview:'پیش‌نمایش پلتفرم',noDraftTitle:'این درخواست تأیید به پیش‌نویسی متصل نیست.',noDraftSub:'یک درخواست جدید از استودیو بسازید.',openStudio:'باز کردن استودیو',noActions:'هنوز عملیاتی ثبت نشده است.',connectTelegramFirst:'ابتدا تلگرام را متصل کنید',connectBaleFirst:'ابتدا بله را متصل کنید',sendTelegram:'ارسال با تلگرام',sendBale:'ارسال با بله',closed:'این درخواست بسته شده است. برای دریافت تصمیم جدید یک نسخه تازه بسازید.',nextAction:'اقدام پیشنهادی بعدی',recommendedTitle:'ادامه راه‌اندازی',recommendedDesc:'برای ادامه روند تأیید، مرحله بعدی آماده را تکمیل کنید.',continue:'ادامه',
    modalSub:'یک پیش‌نویس ذخیره‌شده را انتخاب کنید و در صورت نیاز مشخصات بررسی‌کننده را وارد کنید.',draft:'پیش‌نویس',loadingDrafts:'در حال بارگذاری پیش‌نویس‌ها…',selectDraft:'انتخاب پیش‌نویس',noDrafts:'هیچ پیش‌نویس ذخیره‌شده‌ای موجود نیست.',createStudio:'در استودیو یک پیش‌نویس بسازید.',reviewerName:'نام بررسی‌کننده',reviewerEmail:'ایمیل بررسی‌کننده',reviewerPhone:'شماره تماس بررسی‌کننده',dueDate:'مهلت بررسی',message:'پیام',messagePlaceholder:'توضیح برای بررسی‌کننده',deliveryMethod:'روش ارسال',publicLink:'لینک عمومی',notConnected:'متصل نیست',internalOnly:'فقط داخلی',cancel:'انصراف',creating:'در حال ساخت…',selectDraftError:'ابتدا یک پیش‌نویس ذخیره‌شده انتخاب کنید.',emailError:'ایمیل بررسی‌کننده معتبر نیست.',loadError:'بارگذاری درخواست‌های تأیید انجام نشد.',draftsLoadError:'بارگذاری پیش‌نویس‌های ذخیره‌شده انجام نشد.',publicLinkUnavailable:'برای این درخواست لینک عمومی در دسترس نیست.',commentRequired:'برای این عملیات نوشتن توضیح لازم است.',rejectConfirm:'این درخواست تأیید رد شود؟',createdToast:'درخواست تأیید ساخته شد',done:'انجام شد',sent:'ارسال شد',untitledDraft:'پیش‌نویس بدون عنوان',
    previewMessage:'پیش‌نمایش پیام',previewLinkedIn:'پیش‌نمایش پست لینکدین',previewGoogle:'پیش‌نمایش به‌روزرسانی Google Business',previewEmail:'پیش‌نمایش متن ایمیل',previewSocial:'پیش‌نمایش کپشن شبکه اجتماعی',
    historyActions:{created:'ساخته شد',sent:'ارسال شد',link_rotated:'لینک عمومی تازه شد',feedback_saved:'بازخورد ذخیره شد',approved:'تأیید شد',rejected:'رد شد',changes_requested:'درخواست تغییر ثبت شد'}
  },
  de:{
    title:'Freigabe-Desk',sub:'Senden Sie echte Entwürfe zur Prüfung, erfassen Sie Entscheidungen und speichern Sie Feedback vor der Veröffentlichung.',create:'Freigabeanfrage erstellen',list:'Freigabeliste',search:'Freigaben suchen',empty:'Noch keine Freigabeanfragen',emptySub:'Erstellen Sie die erste Anfrage aus einem gespeicherten Studio-Entwurf.',select:'Freigabeanfrage auswählen',actions:'Kommentare und Aktionen',comment:'Feedback oder gewünschte Änderungen hinzufügen…',approve:'Freigeben',changes:'Änderungen anfordern',reject:'Ablehnen',memory:'Feedback im Smarbiz-Gedächtnis speichern',copy:'Öffentlichen Link kopieren',history:'Verlauf',noComment:'Kein Kommentar',filtered:'Keine Anfragen entsprechen diesen Filtern.',connect:'Freigabemethode verbinden',connectSub:'Öffentliche Links funktionieren sofort. Telegram und Bale benötigen eine konfigurierte Verbindung.',retry:'Erneut versuchen',
    approvals:'Freigaben',all:'Alle',allChannels:'Alle Kanäle',newest:'Neueste',dueSoon:'Bald fällig',statusSort:'Status',noChannel:'Kein Kanal',content:'Inhalt',reviewer:'Prüfer',relatedStudio:'Zugehöriger Studio-Entwurf',relatedCalendar:'Zugehöriger Kalendereintrag',hook:'Einstieg',cta:'CTA',platformPreview:'Plattformvorschau',noDraftTitle:'Diese Freigabeanfrage ist mit keinem Entwurf verknüpft.',noDraftSub:'Erstellen Sie eine neue Anfrage im Studio.',openStudio:'Studio öffnen',noActions:'Noch keine Aktionen.',connectTelegramFirst:'Zuerst Telegram verbinden',connectBaleFirst:'Zuerst Bale verbinden',sendTelegram:'Per Telegram senden',sendBale:'Per Bale senden',closed:'Diese Anfrage ist geschlossen. Erstellen Sie eine neue Version für eine weitere Entscheidung.',nextAction:'Nächster empfohlener Schritt',recommendedTitle:'Einrichtung fortsetzen',recommendedDesc:'Schließen Sie den nächsten verfügbaren Schritt ab, um den Freigabeprozess fortzusetzen.',continue:'Weiter',
    modalSub:'Wählen Sie einen gespeicherten Entwurf und geben Sie optional die Daten des Prüfers an.',draft:'Entwurf',loadingDrafts:'Entwürfe werden geladen…',selectDraft:'Entwurf auswählen',noDrafts:'Keine gespeicherten Entwürfe verfügbar.',createStudio:'Im Studio einen Entwurf erstellen.',reviewerName:'Name des Prüfers',reviewerEmail:'E-Mail des Prüfers',reviewerPhone:'Telefon des Prüfers',dueDate:'Fälligkeitsdatum',message:'Nachricht',messagePlaceholder:'Kontext für den Prüfer',deliveryMethod:'Versandmethode',publicLink:'Öffentlicher Link',notConnected:'nicht verbunden',internalOnly:'Nur intern',cancel:'Abbrechen',creating:'Wird erstellt…',selectDraftError:'Wählen Sie zuerst einen gespeicherten Entwurf.',emailError:'Geben Sie eine gültige E-Mail-Adresse ein.',loadError:'Freigaben konnten nicht geladen werden.',draftsLoadError:'Gespeicherte Entwürfe konnten nicht geladen werden.',publicLinkUnavailable:'Für diese Anfrage ist kein öffentlicher Link verfügbar.',commentRequired:'Für diese Aktion ist ein Kommentar erforderlich.',rejectConfirm:'Diese Freigabeanfrage ablehnen?',createdToast:'Freigabeanfrage erstellt',done:'Erledigt',sent:'Gesendet',untitledDraft:'Unbenannter Entwurf',
    previewMessage:'Nachrichtenvorschau',previewLinkedIn:'LinkedIn-Beitragsvorschau',previewGoogle:'Google-Business-Aktualisierungsvorschau',previewEmail:'E-Mail-Vorschau',previewSocial:'Social-Caption-Vorschau',
    historyActions:{created:'Erstellt',sent:'Gesendet',link_rotated:'Öffentlicher Link erneuert',feedback_saved:'Feedback gespeichert',approved:'Freigegeben',rejected:'Abgelehnt',changes_requested:'Änderungen angefordert'}
  }
};

function normalizeLocale(value:string|string[]|undefined):Locale {
  const locale = Array.isArray(value) ? value[0] : value;
  return locale === 'fa' || locale === 'de' ? locale : 'en';
}

export default function Page() {
  const params = useParams<{locale:string}>();
  const locale = normalizeLocale(params?.locale);
  return <AppShell locale={locale}><Approvals locale={locale}/></AppShell>;
}

function badge(status?:string) {
  if (status === 'approved') return 'badge badge-success';
  if (status === 'rejected' || status === 'expired' || status === 'cancelled') return 'badge border-red-200 bg-red-50 !text-red-700';
  if (status === 'changes_requested') return 'badge badge-warn';
  return 'badge';
}

function normalizeDetail(value:any):Detail|null {
  if (!value || typeof value !== 'object' || value.id == null) return null;
  return {...value, actions:Array.isArray(value.actions) ? value.actions : []} as Detail;
}

function normalizeOverview(value:any):Overview {
  if (!value || typeof value !== 'object') throw new Error('invalid_overview');
  return {
    ...value,
    requests:Array.isArray(value.requests) ? value.requests : [],
    channels:{...disconnectedChannels,...(value.channels || {})},
    selected_request:normalizeDetail(value.selected_request),
  } as Overview;
}

function displayTitle(locale:Locale, title?:string|null) {
  const value = String(title || '').trim();
  if (!value || ['untitled draft','untitled'].includes(value.toLowerCase())) return copy[locale].untitledDraft;
  return value;
}

function contentTypeLabel(locale:Locale, value?:string|null) {
  const key = String(value || '').toLowerCase();
  const labels:any = {
    en:{post:'Post',reel:'Reel',story:'Story',email:'Email',article:'Article',video:'Video',content:'Content'},
    fa:{post:'پست',reel:'ریلز',story:'استوری',email:'ایمیل',article:'مقاله',video:'ویدیو',content:'محتوا'},
    de:{post:'Beitrag',reel:'Reel',story:'Story',email:'E-Mail',article:'Artikel',video:'Video',content:'Inhalt'},
  };
  return labels[locale][key] || value || copy[locale].content;
}

function historyActionLabel(locale:Locale, action:string) {
  return copy[locale].historyActions?.[action] || statusLabel(locale,action);
}

function localizedError(locale:Locale, error:any, fallback:string) {
  const message = String(error?.message || error || '').trim();
  if (!message) return fallback;
  if (locale === 'en') return message;
  if (locale === 'fa' && /[\u0600-\u06ff]/.test(message)) return message;
  return fallback;
}

function Approvals({locale}:{locale:Locale}) {
  const d = t(locale);
  const c = copy[locale];
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
      const o = normalizeOverview(await api.get<Overview>('/approvals/overview'));
      setOverview(o);
      setErr('');
      const id = preferredId || selected?.id || o.selected_request?.id || o.requests[0]?.id;
      if (id) {
        try { setSelected(normalizeDetail(await api.get<Detail>(`/approvals/requests/${id}`))); }
        catch { setSelected(normalizeDetail(o.selected_request)); }
      } else setSelected(null);
    } catch (e:any) {
      setErr(localizedError(locale,e,c.loadError));
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
    try {
      const detail = normalizeDetail(await api.get<Detail>(`/approvals/requests/${id}`));
      if (detail) setSelected(detail);
    } catch (e:any) { toast(localizedError(locale,e,c.loadError)); }
  }

  async function act(kind:'approve'|'request-changes'|'reject') {
    if (!selected) return;
    if ((kind === 'request-changes' || kind === 'reject') && !comment.trim()) {
      toast(c.commentRequired);
      return;
    }
    if (kind === 'reject' && !confirm(c.rejectConfirm)) return;
    setBusy(kind);
    try {
      const result = normalizeDetail(await api.post<Detail>(`/approvals/requests/${selected.id}/${kind}`, {comment: comment.trim() || null}));
      if (result) setSelected(result);
      setComment('');
      toast(kind === 'approve' ? c.approve : kind === 'reject' ? c.reject : c.changes);
      await load(selected.id);
    } catch (e:any) { toast(localizedError(locale,e,c.loadError)); }
    finally { setBusy(''); }
  }

  async function util(kind:'memory'|'copy'|'telegram'|'bale') {
    if (!selected) return;
    setBusy(kind);
    const path = kind === 'memory' ? 'save-feedback-to-memory' : kind === 'copy' ? 'copy-link-event' : kind === 'telegram' ? 'send-via-telegram' : 'send-via-bale';
    try {
      const result = await api.post<any>(`/approvals/requests/${selected.id}/${path}`, {comment: comment.trim() || null});
      if (kind === 'copy') {
        const raw = result?.public_url || result?.approval_url || selected.public_url;
        if (!raw) throw new Error(c.publicLinkUnavailable);
        const url = raw.startsWith('http') ? raw : `${location.origin}/${locale}${raw.startsWith('/') ? raw : `/${raw}`}`;
        await navigator.clipboard.writeText(url);
        toast(c.copy);
      } else if (kind === 'telegram' || kind === 'bale') toast(c.sent);
      else toast(c.done);
      await load(selected.id);
    } catch (e:any) { toast(localizedError(locale,e,kind === 'copy' ? c.publicLinkUnavailable : c.loadError)); }
    finally { setBusy(''); }
  }

  if (loading && !overview) return <div className="space-y-4"><div className="h-10 w-72 animate-pulse rounded-xl bg-slate-200"/><div className="grid gap-5 xl:grid-cols-3"><div className="panel h-72 animate-pulse"/><div className="panel h-72 animate-pulse"/><div className="panel h-72 animate-pulse"/></div></div>;
  if (err && !overview) return <div className="panel p-6"><h1 className="text-2xl font-black">{c.title}</h1><p className="muted mt-2">{err}</p><button className="btn mt-4" onClick={() => load()}>{c.retry}</button></div>;

  const closed = !!selected && ['approved','rejected','expired','cancelled'].includes(selected.status);
  const channels = overview?.channels || disconnectedChannels;
  const availableChannels = [...new Set((overview?.requests || []).map(x => x.channel).filter(Boolean))] as string[];
  const recommendation = overview?.recommended_action && typeof overview.recommended_action === 'object' ? overview.recommended_action : null;

  return <div className="space-y-5">
    <section className="command-card p-6"><div className="flex flex-wrap items-start gap-3"><div><p className="badge">{overview?.organization?.name || d.common.organization}{overview?.brand?.name ? ` · ${overview.brand.name}` : ''}</p><h1 className="mt-3 text-4xl font-black md:text-5xl">{c.title}</h1><p className="muted mt-2 max-w-3xl">{c.sub}</p></div><button className="btn ms-auto" onClick={() => {setForm(emptyCreate);setCreateOpen(true)}}>{c.create}</button></div></section>

    {overview && !channels.telegram_connected && !channels.bale_connected && <div className="panel border-amber-200 bg-amber-50 p-4 text-amber-900"><b>{c.connect}</b><p className="text-sm">{c.connectSub}</p><Link className="chip mt-2" href={`/${locale}/app/integrations`}>{c.connect}</Link></div>}

    {!overview?.requests.length
      ? <section className="panel p-8 text-center"><span className="badge">{c.approvals}</span><h2 className="mt-4 text-3xl font-black">{c.empty}</h2><p className="muted mt-2">{c.emptySub}</p><div className="mt-5 flex flex-wrap justify-center gap-2"><button className="btn" onClick={() => {setForm(emptyCreate);setCreateOpen(true)}}>{c.create}</button><Link className="chip" href={`/${locale}/app/content-studio`}>{d.actions.open}</Link></div></section>
      : <div className="grid gap-5 xl:grid-cols-[22rem_minmax(0,1fr)_22rem]">
        <aside className="panel h-fit p-4 xl:sticky xl:top-24"><h2 className="font-black">{c.list}</h2><input className="field mt-3" value={q} onChange={e => setQ(e.target.value)} placeholder={c.search}/><div className="mt-3 grid grid-cols-2 gap-2"><select className="field" value={status} onChange={e => setStatus(e.target.value)}><option value="all">{c.all}</option>{['pending','changes_requested','approved','rejected','expired','cancelled'].map(x => <option key={x} value={x}>{statusLabel(locale,x)}</option>)}</select><select className="field" value={channel} onChange={e => setChannel(e.target.value)}><option value="all">{c.allChannels}</option>{availableChannels.map(x => <option key={x}>{x}</option>)}</select><select className="field col-span-2" value={sort} onChange={e => setSort(e.target.value)}><option value="newest">{c.newest}</option><option value="due">{c.dueSoon}</option><option value="status">{c.statusSort}</option></select></div><div className="mt-3 max-h-[60vh] space-y-2 overflow-auto">{filtered.length ? filtered.map(x => <button className={`block w-full rounded-xl border p-3 text-start transition ${selected?.id === x.id ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-white hover:bg-slate-50'}`} onClick={() => open(x.id)} key={x.id}><b className="line-clamp-2">{displayTitle(locale,x.title)}</b><p className="muted text-sm">{x.channel || c.noChannel} · {contentTypeLabel(locale,x.content_type)}</p><div className="mt-2 flex items-center justify-between gap-2"><span className={badge(x.status)}>{statusLabel(locale,x.status)}</span>{x.due_at && <span className="muted text-xs">{new Date(x.due_at).toLocaleDateString(locale)}</span>}</div></button>) : <p className="muted rounded-xl bg-slate-50 p-4 text-sm">{c.filtered}</p>}</div></aside>

        <section className="panel min-w-0 p-5 md:p-6"><span className={badge(selected?.status)}>{selected ? statusLabel(locale,selected.status) : c.select}</span><h2 className="mt-4 text-3xl font-black">{selected ? displayTitle(locale,selected.title) : c.select}</h2>{selected?.reviewer && <p className="muted mt-1 text-sm">{c.reviewer}: {selected.reviewer}</p>}
          {selected?.draft ? <div className="mt-5 space-y-4"><div className="flex flex-wrap gap-2"><span className="badge">{selected.channel || c.noChannel}</span><span className="badge">{contentTypeLabel(locale,selected.content_type)}</span><Link className="chip" href={`/${locale}/app/content-studio?draft=${selected.draft.id}`}>{c.relatedStudio}</Link>{selected.calendar_item && <Link className="chip" href={`/${locale}/app/calendar?item=${selected.calendar_item.id}`}>{c.relatedCalendar}</Link>}</div><div className="rounded-2xl border border-slate-200 bg-slate-50 p-5" dir={selected.draft.body?.match(/[\u0600-\u06ff]/) ? 'rtl' : 'auto'}><b>{displayTitle(locale,selected.draft.title)}</b>{selected.draft.hook && <p className="mt-3"><b>{c.hook}:</b> {selected.draft.hook}</p>}<p className="mt-3 whitespace-pre-wrap">{selected.draft.body}</p>{selected.draft.cta && <p className="mt-3"><b>{c.cta}:</b> {selected.draft.cta}</p>}{selected.draft.hashtags && <p className="mt-3 text-blue-700">{selected.draft.hashtags}</p>}</div><div className="rounded-2xl border border-slate-200 p-5"><b>{c.platformPreview}</b><p className="muted mt-1 text-sm">{platformPreview(locale,selected.channel)}</p><p className="mt-3 whitespace-pre-wrap">{selected.draft.body}</p></div></div>
          : selected ? <div className="mt-6 rounded-2xl border border-slate-200 p-6"><b>{c.noDraftTitle}</b><p className="muted">{c.noDraftSub}</p><Link className="btn mt-4" href={`/${locale}/app/content-studio`}>{c.openStudio}</Link></div> : null}
          <div className="mt-6"><h3 className="font-black">{c.history}</h3><div className="mt-2 space-y-2">{selected?.actions?.length ? selected.actions.map(a => <div className="rounded-xl bg-slate-50 p-3" key={a.id}><div className="flex items-center justify-between gap-2"><b>{historyActionLabel(locale,a.action)}</b><span className="muted text-xs">{a.created_at && new Date(a.created_at).toLocaleString(locale)}</span></div><p className="muted mt-1 text-sm">{a.comment || c.noComment}</p></div>) : <p className="muted rounded-xl bg-slate-50 p-3 text-sm">{c.noActions}</p>}</div></div>
        </section>

        <aside className="space-y-5"><div className="panel p-5"><h2 className="font-black">{c.actions}</h2><textarea className="field mt-3 min-h-28" value={comment} onChange={e => setComment(e.target.value)} placeholder={c.comment}/><div className="mt-3 grid gap-2"><button disabled={!selected || closed || !!busy} className="btn disabled:cursor-not-allowed disabled:opacity-50" onClick={() => act('approve')}>{busy === 'approve' ? '…' : c.approve}</button><button disabled={!selected || closed || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => act('request-changes')}>{c.changes}</button><button disabled={!selected || closed || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => act('reject')}>{c.reject}</button><button disabled={!selected || !comment.trim() || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => util('memory')}>{c.memory}</button><button disabled={!selected || !channels.telegram_connected || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" title={!channels.telegram_connected ? c.connectTelegramFirst : ''} onClick={() => util('telegram')}>{c.sendTelegram}</button><button disabled={!selected || !channels.bale_connected || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" title={!channels.bale_connected ? c.connectBaleFirst : ''} onClick={() => util('bale')}>{c.sendBale}</button><button disabled={!selected || !channels.public_link_enabled || !!busy} className="chip disabled:cursor-not-allowed disabled:opacity-50" onClick={() => util('copy')}>{c.copy}</button></div>{closed && <p className="muted mt-3 text-sm">{c.closed}</p>}</div>{recommendation && <div className="panel p-5"><h2 className="font-black">{c.nextAction}</h2><b className="mt-2 block">{locale === 'en' ? (recommendation.title || c.recommendedTitle) : c.recommendedTitle}</b><p className="muted text-sm">{locale === 'en' ? (recommendation.description || c.recommendedDesc) : c.recommendedDesc}</p><Link className="chip mt-3" href={`/${locale}${recommendation.action_href || '/app/integrations'}`}>{locale === 'en' ? (recommendation.action_label || c.continue) : c.continue}</Link></div>}<HelpAside locale={locale} page={c.title}/></aside>
      </div>}

    {createOpen && <CreateModal locale={locale} overview={overview} form={form} setForm={setForm} close={() => setCreateOpen(false)} done={async (result:any) => {setCreateOpen(false);setForm(emptyCreate);toast(c.createdToast);await load(result.id)}}/>}
  </div>;
}

function CreateModal({locale, overview, form, setForm, close, done}:any) {
  const c = copy[locale] || copy.en;
  const channels = overview?.channels || disconnectedChannels;
  const [drafts, setDrafts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState('');
  useEffect(() => {
    api.get<any[]>('/studio/drafts')
      .then(value => setDrafts(Array.isArray(value) ? value : []))
      .catch((e:any) => setErr(localizedError(locale,e,c.draftsLoadError)))
      .finally(() => setLoading(false));
  }, []);
  async function submit() {
    if (!form.draft_id) {setErr(c.selectDraftError);return;}
    if (form.reviewer_email && !/^\S+@\S+\.\S+$/.test(form.reviewer_email)) {setErr(c.emailError);return;}
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
    } catch (e:any) {setErr(localizedError(locale,e,c.loadError));}
    finally {setSubmitting(false);}
  }
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/35 p-4" onClick={close}><div className="panel max-h-[92vh] w-full max-w-2xl overflow-auto p-6" onClick={e => e.stopPropagation()}><div className="flex items-center gap-3"><div><h2 className="text-2xl font-black">{c.create}</h2><p className="muted text-sm">{c.modalSub}</p></div><button className="chip ms-auto" aria-label={c.cancel} onClick={close}>×</button></div>{err && <p className="mt-4 rounded-xl bg-red-50 p-3 text-red-700">{err}</p>}<div className="mt-5 space-y-4"><label className="block text-sm font-bold">{c.draft} *<select className="field mt-2" disabled={loading} value={form.draft_id} onChange={e => setForm({...form,draft_id:e.target.value})}><option value="">{loading ? c.loadingDrafts : c.selectDraft}</option>{drafts.filter(x => !['published','archived'].includes(x.status)).map(x => <option value={x.id} key={x.id}>{displayTitle(locale,x.title)} · {x.channel || c.noChannel} · {statusLabel(locale,x.status)}</option>)}</select></label>{!loading && !drafts.length && <div className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">{c.noDrafts} <Link className="font-bold underline" href={`/${locale}/app/content-studio?new=1`}>{c.createStudio}</Link></div>}<div className="grid gap-4 md:grid-cols-2"><Field label={c.reviewerName} value={form.reviewer_name} onChange={(v:string) => setForm({...form,reviewer_name:v})}/><Field label={c.reviewerEmail} type="email" value={form.reviewer_email} onChange={(v:string) => setForm({...form,reviewer_email:v})}/><Field label={c.reviewerPhone} type="tel" value={form.reviewer_phone} onChange={(v:string) => setForm({...form,reviewer_phone:v})}/><Field label={c.dueDate} type="datetime-local" value={form.due_at} onChange={(v:string) => setForm({...form,due_at:v})}/></div><label className="block text-sm font-bold">{c.message}<textarea className="field mt-2 min-h-24" value={form.message} onChange={e => setForm({...form,message:e.target.value})} placeholder={c.messagePlaceholder}/></label><label className="block text-sm font-bold">{c.deliveryMethod}<select className="field mt-2" value={form.method} onChange={e => setForm({...form,method:e.target.value})}><option value="public_link" disabled={!channels.public_link_enabled}>{c.publicLink}</option><option value="telegram" disabled={!channels.telegram_connected}>Telegram{!channels.telegram_connected ? ` · ${c.notConnected}` : ''}</option><option value="bale" disabled={!channels.bale_connected}>Bale{!channels.bale_connected ? ` · ${c.notConnected}` : ''}</option><option value="internal">{c.internalOnly}</option></select></label></div><div className="mt-6 flex flex-wrap justify-end gap-2"><button className="chip" onClick={close}>{c.cancel}</button><button className="btn" disabled={submitting || !form.draft_id} onClick={submit}>{submitting ? c.creating : c.create}</button></div></div></div>;
}

function platformPreview(locale:Locale, channel?:string) {
  const c = copy[locale];
  const value = channel?.toLowerCase() || '';
  if (value.includes('telegram') || value.includes('bale')) return c.previewMessage;
  if (value.includes('linkedin')) return c.previewLinkedIn;
  if (value.includes('google')) return c.previewGoogle;
  if (value.includes('email')) return c.previewEmail;
  return c.previewSocial;
}
function Field({label, value, onChange, type='text'}:any) {return <label className="block text-sm font-bold">{label}<input className="field mt-2" type={type} value={value || ''} onChange={e => onChange(e.target.value)}/></label>}
