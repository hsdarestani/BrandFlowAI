import '../globals.css';
import {dir,isLocale,getLocaleFontClass} from '@/lib/i18n';
export const metadata={title:'Smarbiz | Content workflow SaaS',description:'Smarbiz runs your content workflow across planning, creation, approvals, publishing, and learning.',metadataBase:new URL('https://smarbiz.sbs'),openGraph:{title:'Smarbiz',description:'Plan faster, create smarter, approve clearly, publish safely.',url:'https://smarbiz.sbs',siteName:'Smarbiz'}};
export default async function LocaleLayout({children,params}:{children:React.ReactNode;params:Promise<{locale:string}>}){const {locale}=await params;const safe=isLocale(locale)?locale:'en';return <html lang={safe} dir={dir(safe)}><body className={getLocaleFontClass(safe)}>{children}</body></html>}
