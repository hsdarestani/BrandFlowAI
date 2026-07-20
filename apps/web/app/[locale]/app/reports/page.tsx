import {AppShell} from '@/components/app-shell';
import {ReportsPage} from '@/components/reports-page';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <AppShell locale={locale}><ReportsPage locale={locale}/></AppShell>;
}
