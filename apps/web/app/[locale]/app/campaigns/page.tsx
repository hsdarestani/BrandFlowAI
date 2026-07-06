import {AppShell} from '@/components/app-shell';import {CampaignsPage} from '@/components/growth/growth-pages';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><CampaignsPage locale={locale}/></AppShell>}
