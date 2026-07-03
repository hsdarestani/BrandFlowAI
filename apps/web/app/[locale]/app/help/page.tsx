import {AppShell} from '@/components/app-shell';import {HelpCenter} from '@/components/help-center';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><HelpCenter locale={locale}/></AppShell>}
