import {AppShell} from '@/components/app-shell';
import {AssetsPage} from '@/components/assets-page';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <AppShell locale={locale}><AssetsPage locale={locale}/></AppShell>;
}
