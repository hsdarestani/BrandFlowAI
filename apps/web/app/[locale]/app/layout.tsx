'use client';

import {use,useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {api,TOKEN_KEY} from '@/lib/api';

export default function AppAreaLayout({children,params}:{children:React.ReactNode;params:Promise<{locale:string}>}){
 const {locale}=use(params);
 const router=useRouter();
 const [checking,setChecking]=useState(true);

 useEffect(()=>{
  let alive=true;
  const token=localStorage.getItem(TOKEN_KEY);
  if(!token){router.replace(`/${locale}/auth/login`);return()=>{alive=false}}

  Promise.all([api.get<any>('/auth/me'),api.get<any>('/brand-pulse/overview')])
   .then(([me,overview])=>{
    if(!alive)return;
    if(me?.is_super_admin){setChecking(false);return}
    const pulse=overview?.pulse||{};
    const hasProduct=(overview?.products||[]).some((item:any)=>String(item?.name||'').trim());
    const coreComplete=Boolean(
     String(pulse.brand_name||'').trim()&&
     String(pulse.brand_summary||'').trim()&&
     String(pulse.target_audience||'').trim()&&
     String(pulse.tone_of_voice||'').trim()&&
     hasProduct
    );
    if(!coreComplete){router.replace(`/${locale}/onboarding`);return}
    setChecking(false);
   })
   .catch((error:any)=>{
    if(!alive)return;
    if(error?.status!==401)router.replace(`/${locale}/onboarding`);
   });

  return()=>{alive=false};
 },[locale,router]);

 if(checking)return <div className="grid min-h-dvh place-items-center px-6" dir={locale==='fa'?'rtl':'ltr'}><div className="text-center"><div className="mx-auto h-11 w-11 animate-spin rounded-full border-[3px] border-slate-200 border-t-indigo-600"/><p className="muted mt-4">{locale==='fa'?'در حال بررسی اطلاعات برند…':locale==='de'?'Markendaten werden geprüft…':'Checking brand setup…'}</p></div></div>;
 return <>{children}</>;
}
