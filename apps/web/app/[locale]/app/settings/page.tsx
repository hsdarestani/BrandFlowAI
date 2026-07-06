import {AppShell} from '@/components/app-shell';import {SettingsPage} from '@/components/settings-page';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><SettingsPage locale={locale}/></AppShell>}
