'use client';

import {use,useEffect,useState} from 'react';
import {useRouter} from 'next/navigation';
import {api,TOKEN_KEY} from '@/lib/api';

const CHAT_DONE_KEY='smarbiz_onboarding_complete_v1';
const needsFocusedOnboarding=(studio:any)=>{
 const missing=studio?.setup?.missing_requirements||[];
 return missing.some((item:any)=>item?.id==='brand_pulse'||item?.id==='product');
};

export default function AppAreaLayout({children,params}:{children:React.ReactNode;params:Promise<{locale:string}>}){
 const {locale}=use(params);
 const router=useRouter();
 const [checking,setChecking]=useState(true);

 useEffect(()=>{
  let alive=true;
  const token=localStorage.getItem(TOKEN_KEY);
  if(!token){router.replace(`/${locale}/auth/login`);return()=>{alive=false}}

  async function check(){
   try{
    const me=await api.get<any>('/auth/me');
    if(!alive)return;
    if(me?.is_super_admin){setChecking(false);return}

    let studio=await api.get<any>('/studio/overview');
    if(!alive)return;

    // The chat writes this marker only after question 10 is successfully saved.
    // Activate non-destructively at that point so legacy/in-progress brands cannot
    // bypass the onboarding chat merely by opening an /app URL directly.
    if(needsFocusedOnboarding(studio)&&localStorage.getItem(CHAT_DONE_KEY)==='1'){
     try{
      await api.post('/onboarding/activate');
      localStorage.removeItem(CHAT_DONE_KEY);
      studio=await api.get<any>('/studio/overview');
     }catch{
      // Keep the user in onboarding if server-side required data is still missing.
     }
    }else if(!needsFocusedOnboarding(studio)){
     localStorage.removeItem(CHAT_DONE_KEY);
    }

    if(!alive)return;
    if(needsFocusedOnboarding(studio)){router.replace(`/${locale}/onboarding`);return}
    setChecking(false);
   }catch(error:any){
    if(!alive)return;
    if(error?.status!==401)router.replace(`/${locale}/onboarding`);
   }
  }

  void check();
  return()=>{alive=false};
 },[locale,router]);

 if(checking)return <div className="grid min-h-dvh place-items-center px-6" dir={locale==='fa'?'rtl':'ltr'}><div className="text-center"><div className="mx-auto h-11 w-11 animate-spin rounded-full border-[3px] border-slate-200 border-t-indigo-600"/><p className="muted mt-4">{locale==='fa'?'در حال بررسی اطلاعات برند…':locale==='de'?'Markendaten werden geprüft…':'Checking brand setup…'}</p></div></div>;
 return <>{children}</>;
}
