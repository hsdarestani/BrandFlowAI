import {StoreLegalPage} from '@/components/store-legal-pages';import {AccountDeletionRequest} from '@/components/account-deletion-request';
export default async function Page({params}:{params:Promise<{locale:string}>}){const {locale}=await params;return <StoreLegalPage locale={locale} kind="deletion"><AccountDeletionRequest locale={locale}/></StoreLegalPage>}
