import {OnboardingWizard} from '@/components/onboarding-wizard';

export default async function Page({params}:{params:Promise<{locale:string}>}){
  const {locale}=await params;
  return <OnboardingWizard locale={locale}/>;
}
