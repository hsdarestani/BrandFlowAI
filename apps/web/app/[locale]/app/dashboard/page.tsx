import {AppShell} from '@/components/app-shell';import {DashboardCockpit} from '@/components/dashboard/dashboard-cockpit';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><DashboardCockpit locale={locale}/></AppShell>}
