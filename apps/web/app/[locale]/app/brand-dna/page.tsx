import {redirect} from 'next/navigation';

export default async function LegacyBrandDnaPage({params,searchParams}:{params:Promise<{locale:string}>;searchParams:Promise<Record<string,string|string[]|undefined>>}){
 const {locale}=await params;
 const query=await searchParams;
 const paramsOut=new URLSearchParams();
 for(const [key,value] of Object.entries(query)){
  if(Array.isArray(value))value.forEach(item=>paramsOut.append(key,item));
  else if(value!==undefined)paramsOut.set(key,value);
 }
 const suffix=paramsOut.toString()?`?${paramsOut.toString()}`:'';
 redirect(`/${locale}/app/brand-pulse${suffix}`);
}
