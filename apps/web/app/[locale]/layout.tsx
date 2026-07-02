import '../globals.css';
const rtl=['fa'];
export default async function LocaleLayout({children,params}:{children:React.ReactNode;params:Promise<{locale:string}>}){const {locale}=await params;return <html lang={locale} dir={rtl.includes(locale)?'rtl':'ltr'}><body>{children}</body></html>}
