import {AppShell} from '@/components/app-shell';import {ContentCalendar} from '@/components/calendar/content-calendar';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <AppShell locale={locale}><ContentCalendar locale={locale}/></AppShell>}
