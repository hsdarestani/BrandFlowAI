import '../globals.css';
import {dir,isLocale} from '@/lib/i18n';
export default async function LocaleLayout({children,params}:{children:React.ReactNode;params:Promise<{locale:string}>}){const {locale}=await params;const safe=isLocale(locale)?locale:'en';return <html lang={safe} dir={dir(safe)}><body>{children}</body></html>}
