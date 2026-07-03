import {AppShell} from '@/components/app-shell';import {AdminCommandCenter} from '@/components/admin/admin-command-center';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><AdminCommandCenter/></AppShell>}
