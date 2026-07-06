import {AppShell} from '@/components/app-shell';import {BrandPulsePage} from '@/components/brand-system-pages';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><BrandPulsePage locale={locale}/></AppShell>}
