'use client';

import Link from 'next/link';
import {useParams, useRouter} from 'next/navigation';
import {useState, type FormEvent} from 'react';
import {LanguageSwitcher} from '@/components/language-switcher';
import {t} from '@/lib/i18n';
import {api, TOKEN_KEY} from '@/lib/api';

const legalCopy: Record<string, string> = {
  en: 'I agree that my account and workspace data will be stored to provide the Smarbiz service.',
  de: 'Ich stimme zu, dass meine Konto- und Workspace-Daten zur Bereitstellung von Smarbiz gespeichert werden.',
  fa: 'موافقم اطلاعات حساب و فضای کاری من برای ارائه سرویس اسماربیز ذخیره شود.',
};

export default function Signup() {
  const {locale} = useParams<{locale: string}>();
  const d = t(locale);
  const router = useRouter();
  const [form, setForm] = useState({
    name: '',
    email: '',
    organization_name: '',
    password: '',
    confirm: '',
    preferred_language: locale,
    terms: false,
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function set(key: string, value: string | boolean) {
    setForm(current => ({...current, [key]: value}));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    if (form.password.length < 8) return setError('Password must contain at least 8 characters.');
    if (form.password !== form.confirm) return setError('Passwords do not match.');
    if (!form.terms) return setError(legalCopy[locale] || legalCopy.en);
    setLoading(true);
    try {
      const payload = {
        name: form.name.trim(),
        email: form.email.trim().toLowerCase(),
        organization_name: form.organization_name.trim(),
        password: form.password,
        preferred_language: form.preferred_language,
        locale: form.preferred_language,
      };
      const res = await api.post<{access_token: string; user: {email: string}}>('/auth/signup', payload);
      if (!res.access_token) throw new Error('Signup response did not include an access token.');
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem('smarbiz_email', res.user.email);
      localStorage.setItem('smarbiz_role', 'owner');
      router.push(`/${locale}/onboarding`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Signup failed. Try another email.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page grid min-h-screen place-items-center p-5">
      <div className="absolute end-5 top-5"><LanguageSwitcher locale={locale}/></div>
      <section className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1fr_.9fr]">
        <div className="command-card relative overflow-hidden p-8">
          <Link href={`/${locale}`} className="flex items-center gap-3"><span className="logo-mark">S</span><b>{d.common.brand}</b></Link>
          <p className="badge mt-8">Smarbiz Workspace</p>
          <h1 className="mt-5 text-4xl font-black md:text-5xl">{d.auth.signupTitle}</h1>
          <p className="muted mt-3 max-w-lg">Create a private workspace, define your brand, and organize the complete content workflow in one place.</p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <Mini icon="⚙️" label="Setup"/><Mini icon="🗓️" label="Plan"/><Mini icon="✅" label="Approve"/>
          </div>
        </div>

        <form onSubmit={submit} className="card p-6 md:p-8">
          <h2 className="text-2xl font-black">Create account</h2>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <Field label={d.auth.name} value={form.name} onChange={value => set('name', value)}/>
            <Field label="Organization" value={form.organization_name} onChange={value => set('organization_name', value)}/>
            <Field label={d.auth.email} type="email" value={form.email} onChange={value => set('email', value)}/>
            <label className="text-sm font-bold">Language
              <select className="field mt-2" value={form.preferred_language} onChange={event => set('preferred_language', event.target.value)}>
                <option value="en">English</option><option value="de">Deutsch</option><option value="fa">فارسی</option>
              </select>
            </label>
            <Field label={d.auth.password} type="password" minLength={8} value={form.password} onChange={value => set('password', value)}/>
            <Field label="Confirm password" type="password" minLength={8} value={form.confirm} onChange={value => set('confirm', value)}/>
          </div>
          <label className="mt-5 flex gap-3 rounded-2xl bg-slate-50 p-3 text-sm">
            <input type="checkbox" checked={form.terms} onChange={event => set('terms', event.target.checked)}/>
            <span>{legalCopy[locale] || legalCopy.en}</span>
          </label>
          {error && <p className="mt-4 rounded-2xl bg-red-50 p-3 text-red-700">{error}</p>}
          <button className="btn mt-6 w-full" disabled={loading}>{loading ? 'Creating…' : d.auth.submitSignup}</button>
          <p className="muted mt-4 text-center text-sm">Already have an account? <Link className="font-bold text-blue-700" href={`/${locale}/auth/login`}>Login</Link></p>
        </form>
      </section>
    </main>
  );
}

function Field({label, type = 'text', minLength, value, onChange}: {label: string; type?: string; minLength?: number; value: string; onChange: (value: string) => void}) {
  return <label className="text-sm font-bold">{label}<input required autoComplete={type === 'password' ? 'new-password' : undefined} className="field mt-2" type={type} minLength={minLength} value={value} onChange={event => onChange(event.target.value)}/></label>;
}

function Mini({icon, label}: {icon: string; label: string}) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-4"><span className="text-2xl">{icon}</span><b className="mt-3 block">{label}</b></div>;
}
