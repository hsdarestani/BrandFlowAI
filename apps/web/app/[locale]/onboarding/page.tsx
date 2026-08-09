import {OnboardingChat} from '@/components/onboarding-chat';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <OnboardingChat locale={locale}/>;
}
