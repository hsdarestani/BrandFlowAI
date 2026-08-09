import {FunctionalIntegrationsPage} from '@/components/functional-integrations-page';

export default function Template({params}:{params:{locale:string};children:React.ReactNode}){
 return <FunctionalIntegrationsPage locale={params.locale}/>;
}
