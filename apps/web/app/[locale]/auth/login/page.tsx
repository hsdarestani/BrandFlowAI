import {LoginScreen} from '@/components/login-screen';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <LoginScreen locale={locale}/>;
}
