import '../globals.css';
import '../mobile-ios.css';
import {Inter,Vazirmatn} from 'next/font/google';
import {dir,isLocale,getLocaleFontClass} from '@/lib/i18n';

const inter=Inter({subsets:['latin'],variable:'--font-inter',display:'swap'});
const vazirmatn=Vazirmatn({subsets:['arabic','latin'],variable:'--font-vazirmatn',display:'swap'});

export const metadata={
 title:'Smarbiz | Content workflow SaaS',
 description:'Smarbiz runs your content workflow across planning, creation, approvals, publishing, and learning.',
 metadataBase:new URL('https://smarbiz.sbs'),
 openGraph:{title:'Smarbiz',description:'Plan faster, create smarter, approve clearly, publish safely.',url:'https://smarbiz.sbs',siteName:'Smarbiz'}
};

export const viewport={
 width:'device-width',
 initialScale:1,
 viewportFit:'cover',
 themeColor:'#f5f7fb'
};

export default async function LocaleLayout({children,params}:{children:React.ReactNode;params:Promise<{locale:string}>}){
 const {locale}=await params;
 const safe=isLocale(locale)?locale:'en';
 return <html lang={safe} dir={dir(safe)} suppressHydrationWarning>
  <body className={`${inter.variable} ${vazirmatn.variable} ${getLocaleFontClass(safe)}`}>{children}</body>
 </html>;
}
