import {AppShell} from '@/components/app-shell';
import {InsightsPage} from '@/components/insights-page';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <AppShell locale={locale}><InsightsPage locale={locale}/></AppShell>;
}
