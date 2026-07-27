'use client';

import {usePathname,useRouter,useSearchParams} from 'next/navigation';
import {startTransition} from 'react';
import {locales,switchLocalePath,type Locale} from '@/lib/i18n';

const labels:Record<Locale,string>={fa:'فا',en:'EN',de:'DE'};
const names:Record<Locale,string>={fa:'فارسی',en:'English',de:'Deutsch'};

export function LanguageSwitcher({locale}:{locale:string}){
 const path=usePathname();const search=useSearchParams();const router=useRouter();
 function change(next:Locale){
  try{localStorage.setItem('smarbiz_locale',next);document.cookie=`smarbiz_locale=${next};path=/;max-age=31536000;SameSite=Lax`}catch{}
  const suffix=search.toString()?`?${search.toString()}`:'';
  startTransition(()=>{router.push(switchLocalePath(path,next)+suffix);router.refresh()});
 }
 return <div className="language-switcher" role="group" aria-label="Language">
  {locales.map(item=><button type="button" key={item} title={names[item]} aria-label={names[item]} aria-current={locale===item?'true':undefined} onClick={()=>change(item)} className={`language-option ${locale===item?'active':''}`}>{labels[item]}</button>)}
 </div>;
}
