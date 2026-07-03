import {AppShell} from '@/components/app-shell';import {ModulePage} from '@/components/dashboard/module-page';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><ModulePage kind="campaigns"/></AppShell>}
