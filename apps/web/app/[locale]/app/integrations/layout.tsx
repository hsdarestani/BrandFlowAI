import {FunctionalIntegrationsPage} from '@/components/functional-integrations-page';

export default async function Layout({params}:{params:Promise<{locale:string}>;children:React.ReactNode}){
 const {locale}=await params;
 return <FunctionalIntegrationsPage locale={locale}/>;
}
