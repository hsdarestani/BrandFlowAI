import {StoreLegalPage} from '@/components/store-legal-pages';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <StoreLegalPage locale={locale} kind="privacy"/>}
