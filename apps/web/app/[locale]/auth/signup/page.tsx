import {SignupScreen} from '@/components/signup-screen';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <SignupScreen locale={locale}/>;
}
