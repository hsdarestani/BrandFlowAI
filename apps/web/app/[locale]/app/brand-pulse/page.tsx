import {AppShell} from '@/components/app-shell';
import {BrandPulseWorkspace} from '@/components/brand-pulse-page';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <AppShell locale={locale}><BrandPulseWorkspace locale={locale}/></AppShell>;
}
