import {PublicApprovalPage} from '@/components/public-approval-page';

export default async function Page({params}:{params:Promise<{locale:string;token:string}>}){
  const {locale,token}=await params;
  return <PublicApprovalPage locale={locale} token={token}/>;
}
