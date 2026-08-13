'use client';
import {useEffect,useState} from 'react';
import Link from 'next/link';
import {api,TOKEN_KEY} from '@/lib/api';

const copy:any={
 en:{loading:'Checking your signed-in workspace…',name:'Workspace name',placeholder:'Type the exact workspace name',button:'Request permanent deletion',busy:'Submitting…',success:'Deletion request recorded. The workspace is marked for permanent deletion.',login:'Sign in to submit from the app',email:'Request deletion by email',mismatch:'The workspace name does not match.',error:'Could not submit the deletion request.'},
 de:{loading:'Angemeldeten Workspace wird geprüft…',name:'Workspace-Name',placeholder:'Exakten Workspace-Namen eingeben',button:'Dauerhafte Löschung anfordern',busy:'Wird gesendet…',success:'Löschanfrage erfasst. Der Workspace ist zur dauerhaften Löschung vorgemerkt.',login:'Anmelden und in der App anfordern',email:'Löschung per E-Mail anfordern',mismatch:'Der Workspace-Name stimmt nicht überein.',error:'Die Löschanfrage konnte nicht gesendet werden.'},
 fa:{loading:'در حال بررسی فضای کاری واردشده…',name:'نام فضای کاری',placeholder:'نام دقیق فضای کاری را وارد کنید',button:'درخواست حذف دائمی',busy:'در حال ارسال…',success:'درخواست حذف ثبت شد و فضای کاری برای حذف دائمی علامت‌گذاری شد.',login:'برای ثبت درخواست وارد شوید',email:'درخواست حذف با ایمیل',mismatch:'نام فضای کاری مطابقت ندارد.',error:'ثبت درخواست حذف انجام نشد.'}
};
export function AccountDeletionRequest({locale}:{locale:string}){
 const c=copy[locale]||copy.en;const [org,setOrg]=useState('');const [typed,setTyped]=useState('');const [state,setState]=useState<'loading'|'guest'|'ready'|'busy'|'done'>('loading');const [error,setError]=useState('');
 useEffect(()=>{if(!localStorage.getItem(TOKEN_KEY)){setState('guest');return}api.get<any>('/settings/overview').then(r=>{setOrg(r.organization?.name||'');setState(r.organization?.name?'ready':'guest')}).catch(()=>setState('guest'))},[]);
 async function submit(){setError('');if(typed.trim()!==org){setError(c.mismatch);return}setState('busy');try{await api.post('/settings/delete-workspace-request',{confirmation:org});setState('done')}catch(e:any){setError(e?.message||c.error);setState('ready')}}
 if(state==='loading')return <p className="muted mt-6">{c.loading}</p>;
 if(state==='guest')return <div className="mt-6 flex flex-wrap gap-3"><Link className="btn" href={`/${locale}/auth/login`}>{c.login}</Link><a className="chip" href="mailto:app@aplus-solution.de?subject=Smarbiz%20account%20deletion">{c.email}</a></div>;
 if(state==='done')return <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 font-bold text-emerald-800">{c.success}</div>;
 return <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5"><label className="block text-sm font-bold">{c.name}<span className="mt-1 block text-xs font-normal text-slate-500">{org}</span><input className="field mt-3 bg-white" value={typed} placeholder={c.placeholder} onChange={e=>setTyped(e.target.value)}/></label>{error&&<p className="mt-3 text-sm font-bold text-red-700">{error}</p>}<button className="btn mt-4 !bg-red-700" disabled={state==='busy'||!typed.trim()} onClick={submit}>{state==='busy'?c.busy:c.button}</button></div>
}
