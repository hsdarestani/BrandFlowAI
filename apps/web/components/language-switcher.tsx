'use client';
import Link from 'next/link';import {usePathname} from 'next/navigation';import {locales,switchLocalePath,type Locale} from '@/lib/i18n';
export function LanguageSwitcher({locale}:{locale:string}){const path=usePathname();return <div className="flex rounded-full border border-white/10 bg-white/5 p-1">{locales.map(l=><Link key={l} href={switchLocalePath(path,l as Locale)} className={`rounded-full px-3 py-1 text-xs font-bold ${locale===l?'bg-cyan-400 text-slate-950':'text-slate-300'}`}>{l.toUpperCase()}</Link>)}</div>}
