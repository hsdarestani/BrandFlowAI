'use client';

import Link from 'next/link';
import {useParams, useRouter} from 'next/navigation';
import {useState, type FormEvent} from 'react';
import {LanguageSwitcher} from '@/components/language-switcher';
import {api, TOKEN_KEY} from '@/lib/api';
import {t} from '@/lib/i18n';

export default function Login() {
  const {locale} = useParams<{locale: string}>();
  const d = t(locale);
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await api.post<{access_token: string; user: {email: string; is_super_admin: boolean}}>(
        '/auth/login',
        {email: email.trim(), password},
      );
      if (!res.access_token) throw new Error(d.auth.loginFailed);
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem('smarbiz_email', res.user.email);
      localStorage.setItem('smarbiz_role', res.user.is_super_admin ? 'super_admin' : 'owner');
      router.push(`/${locale}/app/${res.user.is_super_admin ? 'admin' : 'dashboard'}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : d.auth.loginFailed);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page grid min-h-screen place-items-center p-5">
      <div className="absolute end-5 top-5"><LanguageSwitcher locale={locale}/></div>
      <section className="grid w-full max-w-5xl gap-6 lg:grid-cols-[.9fr_1.1fr]">
        <div className="command-card p-8">
          <Link href={`/${locale}`} className="flex items-center gap-3">
            <span className="logo-mark">S</span><b>Smarbiz</b>
          </Link>
          <h1 className="mt-8 text-4xl font-black">{d.auth.loginTitle}</h1>
          <p className="muted mt-3">Access your private brand workspace and continue planning, creating, and approving content.</p>
          <div className="mt-8 grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <Feature title="Plan" text="Build a focused content calendar."/>
            <Feature title="Create" text="Generate and refine brand-aligned drafts."/>
            <Feature title="Approve" text="Keep every review and decision organized."/>
          </div>
        </div>

        <form onSubmit={submit} className="card p-8">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-black">{d.auth.workspaceLogin}</h2>
            <span className="badge">{d.auth.secure}</span>
          </div>
          <label className="text-sm font-bold">{d.auth.email}</label>
          <input required autoComplete="email" className="field mt-2" type="email" value={email} onChange={event => setEmail(event.target.value)}/>
          <label className="mt-4 block text-sm font-bold">{d.auth.password}</label>
          <div className="mt-2 flex gap-2">
            <input required autoComplete="current-password" className="field" type={show ? 'text' : 'password'} value={password} onChange={event => setPassword(event.target.value)}/>
            <button type="button" className="chip" onClick={() => setShow(!show)}>{show ? d.auth.hide : d.auth.show}</button>
          </div>
          {error && <p className="mt-4 rounded-2xl bg-red-500/10 p-3 text-red-700">{error}</p>}
          <button className="btn mt-6 w-full" disabled={loading}>{loading ? d.auth.signingIn : d.auth.submitLogin}</button>
          <p className="muted mt-4 text-center text-sm">
            {d.auth.newAccount} <Link className="font-bold text-blue-700" href={`/${locale}/auth/signup`}>{d.auth.createAccount}</Link>
          </p>
        </form>
      </section>
    </main>
  );
}

function Feature({title, text}: {title: string; text: string}) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-4"><b>{title}</b><p className="muted mt-1 text-sm">{text}</p></div>;
}
