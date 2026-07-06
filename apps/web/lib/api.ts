export type ApiOptions = RequestInit & { mockFallback?: unknown; authenticated?: boolean };
const baseUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/\/$/, '');
export class ApiError extends Error{status:number;detail:any;constructor(status:number,message:string,detail?:any){super(message);this.status=status;this.detail=detail}}
export const TOKEN_KEY='smarbiz_token';
export const SESSION_MESSAGE_KEY='smarbiz_session_message';
function browser(){return typeof window !== 'undefined'}
function currentLocale(){if(!browser())return 'en';return location.pathname.split('/').filter(Boolean)[0]||'en'}
export function getToken(){ if (!browser()) return ''; return localStorage.getItem(TOKEN_KEY) || ''; }
const networkMessages:any={en:'Could not connect to the backend. Please check your connection and try again.',fa:'اتصال به سرور برقرار نشد. لطفاً اتصال خود را بررسی کنید و دوباره تلاش کنید.',de:'Die Verbindung zum Server konnte nicht hergestellt werden. Bitte prüfen Sie Ihre Verbindung und versuchen Sie es erneut.'};
const sessionMessages:any={en:'Session expired. Please log in again.',fa:'نشست شما منقضی شده است. لطفاً دوباره وارد شوید.',de:'Ihre Sitzung ist abgelaufen. Bitte melden Sie sich erneut an.'};
export function localizedNetworkMessage(locale=currentLocale()){return networkMessages[locale]||networkMessages.en}
export function clearSession(){ if(browser()){const l=currentLocale();localStorage.removeItem(TOKEN_KEY);localStorage.setItem(SESSION_MESSAGE_KEY,sessionMessages[l]||sessionMessages.en)}}
export function redirectToLogin(){ if(browser()){const l=currentLocale(); if(!location.pathname.includes('/auth/login')) location.href=`/${l}/auth/login`;}}
async function request<T>(path:string, options:ApiOptions={}){
  const isForm=typeof FormData!=='undefined' && options.body instanceof FormData;
  const jwt=getToken();
  const headers:HeadersInit={...(isForm?{}:{'Content-Type':'application/json'}),...(jwt?{Authorization:`Bearer ${jwt}`}:{ }),...(options.headers||{})};
  try{
    const res=await fetch(`${baseUrl}${path}`,{...options,headers});
    if(res.status===401){clearSession(); redirectToLogin(); throw new ApiError(401,sessionMessages[currentLocale()]||sessionMessages.en);}
    if(!res.ok){let detail:any; try{detail=await res.json()}catch{detail=await res.text()} const msg=detail?.detail?.message||detail?.message||detail?.detail||String(detail)||`Request failed (${res.status})`; throw new ApiError(res.status,msg,detail)}
    if(res.status===204) return undefined as T;
    return await res.json() as T;
  }catch(e){ if('mockFallback' in options && !(e instanceof ApiError && e.status===401)) return options.mockFallback as T; if(e instanceof TypeError && String(e.message).includes('fetch')) throw new ApiError(0,localizedNetworkMessage(),e); throw e; }
}
export const api={baseUrl,get:<T>(p:string,o?:ApiOptions)=>request<T>(p,o),post:<T>(p:string,b?:unknown,o?:ApiOptions)=>request<T>(p,{...o,method:'POST',body:b instanceof FormData?b:JSON.stringify(b||{})}),patch:<T>(p:string,b?:unknown,o?:ApiOptions)=>request<T>(p,{...o,method:'PATCH',body:b instanceof FormData?b:JSON.stringify(b||{})}),delete:<T>(p:string,o?:ApiOptions)=>request<T>(p,{...o,method:'DELETE'})};

export type HomeOverview={user:{id:number;name:string;email:string};organization:{id:number;name:string;mode?:string}|null;brand:{id:number;name:string;industry?:string;primary_language?:string;setup_status?:string}|null;setup:{completion_percent:number;first_incomplete_step_id:string|null;steps:{id:string;title:string;description:string;status:'done'|'in_progress'|'not_started';estimated_time_minutes?:number;action_label:string;action_href:string}[]};kpis:{id:string;label:string;value:string|number;delta?:string|null;tone?:'neutral'|'good'|'warning';href?:string;helper?:string}[];weekly_activity:{day:string;generated:number;approved:number;published:number}[];pipeline:{status:string;label:string;count:number;href:string;items:{id:number|string;title:string;channel?:string;priority?:string;href:string}[]}[];recent_work:{id:string|number;title:string;type:string;status:string;channel?:string;score?:number|null;updated_at?:string;href:string}[];recommended_action:{title:string;description:string;action_label:string;action_href:string;severity:'info'|'warning'|'success';missing_requirements?:string[]};alerts:{id:string;title:string;description:string;severity:'info'|'warning'|'success'|'danger';href?:string}[];memory_summary?:{title:string;description:string;href:string};channel_health?:{title:string;description:string;status:'good'|'warning'|'missing';href:string};approval_status_summary?:{pending:number;approved:number;total:number}};
export const fetchHomeOverview=()=>api.get<HomeOverview>('/dashboard/home');
