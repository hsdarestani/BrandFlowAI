'use client';

import {useEffect, useMemo, useState} from 'react';
import {useParams, useRouter} from 'next/navigation';
import {LanguageSwitcher} from '@/components/language-switcher';
import {api} from '@/lib/api';

type Locale = 'en' | 'fa' | 'de';
type SetupForm = {
  organization_name: string;
  workspace_mode: 'owner' | 'agency';
  brand_name: string;
  website_url: string;
  industry: string;
  country: string;
  timezone: string;
  primary_language: Locale;
  brand_summary: string;
  target_audience: string;
  audience_pain_points: string;
  desired_outcomes: string;
  tone_of_voice: string;
  writing_style: string;
  content_pillars: string;
  value_propositions: string;
  forbidden_claims: string;
  product_name: string;
  product_description: string;
  channels: string[];
  approval_method: 'public_link' | 'telegram' | 'bale' | 'internal';
  generate_first_week: boolean;
};

const emptyForm: SetupForm = {
  organization_name: '',
  workspace_mode: 'owner',
  brand_name: '',
  website_url: '',
  industry: '',
  country: 'DE',
  timezone: 'Europe/Berlin',
  primary_language: 'en',
  brand_summary: '',
  target_audience: '',
  audience_pain_points: '',
  desired_outcomes: '',
  tone_of_voice: '',
  writing_style: '',
  content_pillars: '',
  value_propositions: '',
  forbidden_claims: '',
  product_name: '',
  product_description: '',
  channels: ['instagram'],
  approval_method: 'public_link',
  generate_first_week: true,
};

const copy = {
  en: {
    title: 'Set up your Smarbiz workspace',
    subtitle: 'Give Smarbiz the minimum real context it needs to plan useful content. You can refine everything later.',
    loading: 'Loading your workspace…',
    save: 'Save progress',
    saving: 'Saving…',
    saved: 'Progress saved',
    back: 'Back',
    next: 'Continue',
    finish: 'Finish setup',
    dashboard: 'Save and open dashboard',
    required: 'Complete the required fields before continuing.',
    failed: 'The setup could not be saved. Your entries are still kept on this device.',
    steps: ['Workspace', 'Brand basics', 'Audience & voice', 'Offer', 'Channels & approval', 'Review'],
    descriptions: [
      'Choose how you will use the workspace.',
      'Add the brand identity and operating defaults.',
      'Define who you serve and how the brand should sound.',
      'Add the first real product or service Smarbiz can promote.',
      'Choose target channels and a review path.',
      'Review the setup and generate the first useful workspace data.',
    ],
  },
  fa: {
    title: 'راه‌اندازی فضای کاری اسماربیز',
    subtitle: 'حداقل اطلاعات واقعی لازم برای برنامه‌ریزی محتوای مفید را وارد کنید. بعداً همه موارد قابل ویرایش‌اند.',
    loading: 'در حال دریافت اطلاعات فضای کاری…',
    save: 'ذخیره پیشرفت',
    saving: 'در حال ذخیره…',
    saved: 'پیشرفت ذخیره شد',
    back: 'قبلی',
    next: 'ادامه',
    finish: 'تکمیل راه‌اندازی',
    dashboard: 'ذخیره و ورود به داشبورد',
    required: 'فیلدهای ضروری این مرحله را کامل کنید.',
    failed: 'ذخیره روی سرور انجام نشد؛ اطلاعات واردشده روی همین دستگاه نگه داشته شده است.',
    steps: ['فضای کاری', 'مشخصات برند', 'مخاطب و لحن', 'محصول/خدمت', 'کانال و تأیید', 'بازبینی'],
    descriptions: [
      'مشخص کنید فضای کاری برای برند خودتان است یا مدیریت چند برند.',
      'هویت برند و تنظیمات اصلی را ثبت کنید.',
      'مخاطب و شیوه صحبت‌کردن برند را تعریف کنید.',
      'اولین محصول یا خدمت واقعی را اضافه کنید.',
      'کانال‌های هدف و مسیر تأیید محتوا را انتخاب کنید.',
      'اطلاعات را مرور کنید و اولین داده‌های قابل استفاده را بسازید.',
    ],
  },
  de: {
    title: 'Smarbiz-Arbeitsbereich einrichten',
    subtitle: 'Geben Sie Smarbiz den wichtigsten echten Kontext für brauchbare Content-Planung. Alles kann später verfeinert werden.',
    loading: 'Arbeitsbereich wird geladen…',
    save: 'Fortschritt speichern',
    saving: 'Wird gespeichert…',
    saved: 'Fortschritt gespeichert',
    back: 'Zurück',
    next: 'Weiter',
    finish: 'Einrichtung abschließen',
    dashboard: 'Speichern und Dashboard öffnen',
    required: 'Bitte füllen Sie die Pflichtfelder dieses Schritts aus.',
    failed: 'Die Einrichtung konnte nicht auf dem Server gespeichert werden. Ihre Eingaben bleiben auf diesem Gerät erhalten.',
    steps: ['Workspace', 'Marke', 'Zielgruppe & Ton', 'Angebot', 'Kanäle & Freigabe', 'Prüfen'],
    descriptions: [
      'Wählen Sie, wie Sie den Workspace verwenden.',
      'Erfassen Sie Markenidentität und Standardwerte.',
      'Definieren Sie Zielgruppe und Markenstimme.',
      'Fügen Sie das erste echte Produkt oder die erste Dienstleistung hinzu.',
      'Wählen Sie Zielkanäle und einen Freigabeweg.',
      'Prüfen Sie die Angaben und erstellen Sie die ersten nutzbaren Daten.',
    ],
  },
};

const channels = ['instagram', 'telegram', 'bale', 'linkedin', 'google_business', 'email', 'blog'];
const multiFields = ['audience_pain_points', 'desired_outcomes', 'content_pillars', 'value_propositions', 'forbidden_claims'] as const;
const toList = (value: string) => value.split(/\n|,/).map(x => x.trim()).filter(Boolean);
const localKey = 'smarbiz_onboarding_draft_v2';

export default function Onboarding() {
  const {locale: rawLocale} = useParams<{locale: string}>();
  const locale: Locale = rawLocale === 'fa' || rawLocale === 'de' ? rawLocale : 'en';
  const c = copy[locale];
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<SetupForm>({...emptyForm, primary_language: locale});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [server, setServer] = useState<any>({settings: null, pulse: null, integrations: null});

  useEffect(() => {
    let alive = true;
    Promise.all([
      api.get<any>('/settings/overview'),
      api.get<any>('/brand-pulse/overview'),
      api.get<any>('/integrations/overview').catch(() => null),
    ]).then(([settings, pulse, integrations]) => {
      if (!alive) return;
      const p = pulse?.pulse || {};
      const stored = typeof window !== 'undefined' ? localStorage.getItem(localKey) : null;
      const local = stored ? JSON.parse(stored) : {};
      setServer({settings, pulse, integrations});
      setForm({
        ...emptyForm,
        primary_language: locale,
        organization_name: settings?.organization?.name || '',
        workspace_mode: settings?.organization?.mode === 'agency' ? 'agency' : 'owner',
        brand_name: p.brand_name || settings?.brand?.name || '',
        website_url: p.website_url || '',
        industry: p.industry || settings?.brand?.industry || '',
        country: p.country || settings?.brand?.country || 'DE',
        timezone: p.timezone || settings?.brand?.timezone || settings?.preferences?.default_timezone || 'Europe/Berlin',
        primary_language: p.primary_language || settings?.brand?.primary_language || locale,
        brand_summary: p.brand_summary || '',
        target_audience: p.target_audience || '',
        audience_pain_points: Array.isArray(p.audience_pain_points) ? p.audience_pain_points.join('\n') : p.audience_pain_points || '',
        desired_outcomes: Array.isArray(p.desired_outcomes) ? p.desired_outcomes.join('\n') : p.desired_outcomes || '',
        tone_of_voice: p.tone_of_voice || '',
        writing_style: p.writing_style || '',
        content_pillars: Array.isArray(p.content_pillars) ? p.content_pillars.join('\n') : p.content_pillars || '',
        value_propositions: Array.isArray(p.value_propositions) ? p.value_propositions.join('\n') : p.value_propositions || '',
        forbidden_claims: Array.isArray(p.forbidden_claims) ? p.forbidden_claims.join('\n') : p.forbidden_claims || '',
        product_name: pulse?.products?.[0]?.name || '',
        product_description: pulse?.products?.[0]?.description || '',
        channels: integrations?.catalog?.filter((x: any) => x.connection_id).map((x: any) => x.provider).filter((x: string) => channels.includes(x)) || ['instagram'],
        approval_method: integrations?.catalog?.find((x: any) => ['approval_link', 'telegram', 'bale'].includes(x.provider) && x.connection_id)?.provider || 'public_link',
        generate_first_week: true,
        ...local,
      });
    }).catch((e: any) => setError(e?.message || c.failed)).finally(() => alive && setLoading(false));
    return () => { alive = false; };
  }, [locale]);

  useEffect(() => {
    if (!loading && typeof window !== 'undefined') localStorage.setItem(localKey, JSON.stringify(form));
  }, [form, loading]);

  const progress = Math.round(((step + 1) / c.steps.length) * 100);
  const requiredValid = useMemo(() => {
    if (step === 0) return !!form.organization_name.trim();
    if (step === 1) return !!form.brand_name.trim() && !!form.industry.trim() && !!form.country.trim() && !!form.timezone.trim();
    if (step === 2) return !!form.brand_summary.trim() && !!form.target_audience.trim() && !!form.tone_of_voice.trim();
    if (step === 3) return !!form.product_name.trim() && !!form.product_description.trim();
    if (step === 4) return form.channels.length > 0 && !!form.approval_method;
    return true;
  }, [form, step]);

  function update<K extends keyof SetupForm>(key: K, value: SetupForm[K]) {
    setForm(current => ({...current, [key]: value}));
    setMessage('');
    setError('');
  }

  async function saveProgress(final = false) {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      await api.patch('/settings/organization', {name: form.organization_name.trim(), mode: form.workspace_mode});
      await api.patch('/settings/brand-defaults', {
        name: form.brand_name.trim(),
        industry: form.industry.trim(),
        country: form.country.trim(),
        timezone: form.timezone.trim(),
        primary_language: form.primary_language,
      });
      await api.patch('/settings/profile', {locale: form.primary_language, timezone: form.timezone.trim()});
      await api.patch('/brand-pulse', {
        brand_name: form.brand_name.trim(),
        website_url: form.website_url.trim(),
        industry: form.industry.trim(),
        country: form.country.trim(),
        timezone: form.timezone.trim(),
        primary_language: form.primary_language,
        brand_summary: form.brand_summary.trim(),
        target_audience: form.target_audience.trim(),
        audience_pain_points: toList(form.audience_pain_points),
        desired_outcomes: toList(form.desired_outcomes),
        tone_of_voice: form.tone_of_voice.trim(),
        writing_style: form.writing_style.trim(),
        content_pillars: toList(form.content_pillars),
        value_propositions: toList(form.value_propositions),
        forbidden_claims: toList(form.forbidden_claims),
        channel_notes: form.channels,
        approval_preferences: form.approval_method,
      });

      const existingProduct = server.pulse?.products?.some((x: any) => x.name?.trim().toLowerCase() === form.product_name.trim().toLowerCase());
      if (form.product_name.trim() && !existingProduct) {
        await api.post('/brand-pulse/products', {
          name: form.product_name.trim(),
          type: 'service',
          description: form.product_description.trim(),
          benefits: toList(form.value_propositions),
          audience: form.target_audience.trim(),
          objections: [],
          proof_points: [],
          status: 'active',
        });
      }

      if (final) {
        const wantedProvider = form.approval_method === 'public_link' ? 'approval_link' : form.approval_method;
        const alreadyConnected = server.integrations?.catalog?.some((x: any) => x.provider === wantedProvider && x.connection_id);
        if (!alreadyConnected && wantedProvider !== 'internal') {
          await api.post('/integrations/connections', {
            provider: wantedProvider,
            display_name: wantedProvider === 'approval_link' ? 'Public approval link' : wantedProvider,
            config: {},
            capabilities: ['approval'],
          }).catch(() => null);
        }
        if (form.generate_first_week) {
          await api.post('/calendar/generate-week', {week_start: new Date().toISOString()}).catch(() => null);
        }
        localStorage.removeItem(localKey);
      }
      setMessage(c.saved);
      return true;
    } catch (e: any) {
      setError(e?.message || c.failed);
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function next() {
    if (!requiredValid) {
      setError(c.required);
      return;
    }
    const ok = await saveProgress(false);
    if (ok) setStep(x => Math.min(c.steps.length - 1, x + 1));
  }

  async function finish() {
    if (!requiredValid) {
      setError(c.required);
      return;
    }
    if (await saveProgress(true)) router.push(`/${locale}/app/dashboard`);
  }

  if (loading) return <main className="min-h-screen bg-app p-5"><div className="mx-auto max-w-6xl"><div className="command-card h-28 animate-pulse"/><div className="mt-6 grid gap-5 lg:grid-cols-[18rem_1fr]"><div className="panel h-96 animate-pulse"/><div className="panel h-[34rem] animate-pulse"/></div><p className="muted mt-5 text-center">{c.loading}</p></div></main>;

  return <main className="min-h-screen bg-app p-4 md:p-6" dir={locale === 'fa' ? 'rtl' : 'ltr'}>
    <div className="mx-auto max-w-7xl">
      <header className="flex items-center gap-3 px-1 py-2">
        <span className="logo-mark">S</span>
        <div><b>Smarbiz</b><p className="muted text-xs">Content operations workspace</p></div>
        <div className="ms-auto"><LanguageSwitcher locale={locale}/></div>
      </header>

      <section className="command-card mt-5 overflow-hidden p-5 md:p-7">
        <div className="flex flex-wrap items-start gap-4">
          <div className="max-w-3xl">
            <span className="badge">{progress}%</span>
            <h1 className="mt-4 text-4xl font-black md:text-6xl">{c.title}</h1>
            <p className="muted mt-3 text-base md:text-lg">{c.subtitle}</p>
          </div>
          <button className="chip ms-auto" disabled={saving} onClick={() => saveProgress(false)}>{saving ? c.saving : c.save}</button>
        </div>
        <div className="mt-6 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-gradient-to-r from-blue-600 to-cyan-400 transition-all" style={{width: `${progress}%`}}/></div>
      </section>

      {(error || message) && <div className={`mt-4 rounded-2xl border p-4 text-sm ${error ? 'border-red-200 bg-red-50 text-red-700' : 'border-green-200 bg-green-50 text-green-800'}`}>{error || message}</div>}

      <section className="mt-5 grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)_19rem]">
        <nav className="panel h-fit p-3 lg:sticky lg:top-4">
          {c.steps.map((label, index) => <button key={label} onClick={() => setStep(index)} className={`mb-1 flex w-full items-start gap-3 rounded-2xl p-3 text-start transition ${index === step ? 'bg-blue-50 text-blue-800 ring-1 ring-blue-100' : 'hover:bg-slate-50'}`}>
            <span className={`grid h-8 w-8 shrink-0 place-items-center rounded-xl text-sm font-black ${index < step ? 'bg-green-100 text-green-700' : index === step ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'}`}>{index < step ? '✓' : index + 1}</span>
            <span><b className="block text-sm">{label}</b><span className="muted mt-1 block text-xs leading-5">{c.descriptions[index]}</span></span>
          </button>)}
        </nav>

        <section className="panel min-h-[36rem] p-5 md:p-7">
          <div className="mb-6"><span className="badge">{step + 1} / {c.steps.length}</span><h2 className="mt-3 text-3xl font-black">{c.steps[step]}</h2><p className="muted mt-2">{c.descriptions[step]}</p></div>
          {step === 0 && <WorkspaceStep form={form} update={update} locale={locale}/>} 
          {step === 1 && <BrandStep form={form} update={update} locale={locale}/>} 
          {step === 2 && <VoiceStep form={form} update={update} locale={locale}/>} 
          {step === 3 && <OfferStep form={form} update={update} locale={locale}/>} 
          {step === 4 && <ChannelsStep form={form} update={update} locale={locale}/>} 
          {step === 5 && <ReviewStep form={form} update={update} locale={locale}/>} 
          <div className="mt-8 flex flex-wrap gap-2 border-t border-slate-200 pt-5">
            <button className="chip" disabled={step === 0 || saving} onClick={() => setStep(x => Math.max(0, x - 1))}>{c.back}</button>
            {step < c.steps.length - 1
              ? <button className="btn ms-auto" disabled={saving} onClick={next}>{saving ? c.saving : c.next}</button>
              : <button className="btn ms-auto" disabled={saving} onClick={finish}>{saving ? c.saving : c.dashboard}</button>}
          </div>
        </section>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:h-fit">
          <div className="learning-card p-5">
            <h3 className="text-lg font-black">Live setup summary</h3>
            <dl className="mt-4 space-y-3 text-sm">
              <Summary label="Workspace" value={form.organization_name}/>
              <Summary label="Brand" value={form.brand_name}/>
              <Summary label="Audience" value={form.target_audience}/>
              <Summary label="Offer" value={form.product_name}/>
              <Summary label="Channels" value={form.channels.join(', ')}/>
              <Summary label="Approval" value={form.approval_method.replaceAll('_', ' ')}/>
            </dl>
          </div>
          <div className="panel p-5"><b>What becomes usable after setup?</b><ul className="muted mt-3 space-y-2 text-sm"><li>• Brand-aware content generation</li><li>• Weekly content calendar</li><li>• Draft approval links</li><li>• Campaign and report context</li></ul></div>
        </aside>
      </section>
    </div>
  </main>;
}

function WorkspaceStep({form, update, locale}: any) {
  const modes = locale === 'fa'
    ? [['owner', 'برند خودم', 'برای مدیریت محتوا و کمپین یک کسب‌وکار.'], ['agency', 'آژانس / چند برند', 'برای مدیریت چند مشتری و مسیرهای تأیید.']]
    : locale === 'de'
      ? [['owner', 'Eigene Marke', 'Content und Kampagnen für ein Unternehmen verwalten.'], ['agency', 'Agentur / mehrere Marken', 'Mehrere Kunden und Freigabewege verwalten.']]
      : [['owner', 'My own brand', 'Manage content and campaigns for one business.'], ['agency', 'Agency / multiple brands', 'Manage multiple clients and approval paths.']];
  return <div className="space-y-5"><Field label="Organization name *" value={form.organization_name} onChange={(v: string) => update('organization_name', v)}/><div className="grid gap-3 md:grid-cols-2">{modes.map(([value, title, description]) => <button type="button" key={value} onClick={() => update('workspace_mode', value)} className={`rounded-2xl border p-5 text-start transition ${form.workspace_mode === value ? 'border-blue-400 bg-blue-50 ring-2 ring-blue-100' : 'border-slate-200 bg-white hover:border-blue-200'}`}><b>{title}</b><p className="muted mt-2 text-sm">{description}</p></button>)}</div></div>;
}
function BrandStep({form, update}: any) {return <div className="grid gap-4 md:grid-cols-2"><Field label="Brand name *" value={form.brand_name} onChange={(v: string) => update('brand_name', v)}/><Field label="Website" value={form.website_url} type="url" onChange={(v: string) => update('website_url', v)}/><Field label="Industry *" value={form.industry} onChange={(v: string) => update('industry', v)}/><Field label="Country *" value={form.country} onChange={(v: string) => update('country', v)}/><Select label="Primary language" value={form.primary_language} options={['en', 'fa', 'de']} onChange={(v: Locale) => update('primary_language', v)}/><Field label="Timezone *" value={form.timezone} onChange={(v: string) => update('timezone', v)}/></div>}
function VoiceStep({form, update}: any) {return <div className="space-y-4"><TextArea label="Brand summary *" value={form.brand_summary} onChange={(v: string) => update('brand_summary', v)}/><TextArea label="Target audience *" value={form.target_audience} onChange={(v: string) => update('target_audience', v)}/><div className="grid gap-4 md:grid-cols-2"><TextArea label="Audience pain points" hint="One per line" value={form.audience_pain_points} onChange={(v: string) => update('audience_pain_points', v)}/><TextArea label="Desired outcomes" hint="One per line" value={form.desired_outcomes} onChange={(v: string) => update('desired_outcomes', v)}/><TextArea label="Tone of voice *" value={form.tone_of_voice} onChange={(v: string) => update('tone_of_voice', v)}/><TextArea label="Writing style" value={form.writing_style} onChange={(v: string) => update('writing_style', v)}/></div></div>}
function OfferStep({form, update}: any) {return <div className="space-y-4"><Field label="Product or service name *" value={form.product_name} onChange={(v: string) => update('product_name', v)}/><TextArea label="Description *" value={form.product_description} onChange={(v: string) => update('product_description', v)}/><div className="grid gap-4 md:grid-cols-2"><TextArea label="Value propositions" hint="One per line" value={form.value_propositions} onChange={(v: string) => update('value_propositions', v)}/><TextArea label="Content pillars" hint="One per line" value={form.content_pillars} onChange={(v: string) => update('content_pillars', v)}/></div><TextArea label="Forbidden or risky claims" hint="One per line" value={form.forbidden_claims} onChange={(v: string) => update('forbidden_claims', v)}/></div>}
function ChannelsStep({form, update}: any) {return <div className="space-y-6"><div><b>Target content channels *</b><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{channels.map(channel => {const active = form.channels.includes(channel);return <button type="button" key={channel} onClick={() => update('channels', active ? form.channels.filter((x: string) => x !== channel) : [...form.channels, channel])} className={`rounded-2xl border p-4 text-start ${active ? 'border-blue-400 bg-blue-50 text-blue-800' : 'border-slate-200 bg-white'}`}><b>{channel.replaceAll('_', ' ')}</b><p className="muted mt-1 text-xs">{active ? 'Selected' : 'Select channel'}</p></button>})}</div></div><Select label="Approval method" value={form.approval_method} options={['public_link', 'telegram', 'bale', 'internal']} onChange={(v: any) => update('approval_method', v)}/><p className="rounded-2xl bg-amber-50 p-4 text-sm text-amber-900">Public approval links work without external credentials. Telegram and Bale still require a valid bot/channel configuration in Integrations.</p></div>}
function ReviewStep({form, update}: any) {return <div className="space-y-5"><div className="grid gap-3 md:grid-cols-2"><Review title="Workspace" value={`${form.organization_name} · ${form.workspace_mode}`}/><Review title="Brand" value={`${form.brand_name} · ${form.industry} · ${form.primary_language}`}/><Review title="Audience" value={form.target_audience}/><Review title="Offer" value={`${form.product_name}: ${form.product_description}`}/><Review title="Channels" value={form.channels.join(', ')}/><Review title="Approval" value={form.approval_method.replaceAll('_', ' ')}/></div><label className="flex gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4"><input type="checkbox" checked={form.generate_first_week} onChange={e => update('generate_first_week', e.target.checked)}/><span><b>Generate the first content week</b><span className="muted mt-1 block text-sm">Smarbiz will create initial calendar ideas using the brand context above. You can edit or delete them.</span></span></label></div>}
function Field({label, value, onChange, type = 'text'}: any) {return <label className="block text-sm font-bold">{label}<input dir="auto" className="field mt-2" type={type} value={value || ''} onChange={e => onChange(e.target.value)}/></label>}
function TextArea({label, value, onChange, hint}: any) {return <label className="block text-sm font-bold">{label}{hint && <span className="muted ms-2 text-xs font-normal">{hint}</span>}<textarea dir="auto" className="field mt-2 min-h-28" value={value || ''} onChange={e => onChange(e.target.value)}/></label>}
function Select({label, value, options, onChange}: any) {return <label className="block text-sm font-bold">{label}<select className="field mt-2" value={value} onChange={e => onChange(e.target.value)}>{options.map((x: string) => <option key={x} value={x}>{x.replaceAll('_', ' ')}</option>)}</select></label>}
function Summary({label, value}: any) {return <div><dt className="muted text-xs">{label}</dt><dd className="mt-1 line-clamp-2 font-semibold">{value || '—'}</dd></div>}
function Review({title, value}: any) {return <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4"><b>{title}</b><p className="muted mt-2 whitespace-pre-wrap text-sm">{value || '—'}</p></div>}
