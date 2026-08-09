import {AppShell} from '@/components/app-shell';
import {FunctionalIntegrationsPage} from '@/components/functional-integrations-page';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <AppShell locale={locale}><FunctionalIntegrationsPage locale={locale}/></AppShell>;
}
