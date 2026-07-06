export type ApiOptions = RequestInit & { mockFallback?: unknown };
const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
function token(){ if (typeof window === 'undefined') return ''; return localStorage.getItem('smarbiz_token') || ''; }
async function request<T>(path:string, options:ApiOptions={}){
  try{
    const isForm=typeof FormData!=='undefined' && options.body instanceof FormData;
    const res=await fetch(`${baseUrl}${path}`,{...options,headers:{...(isForm?{}:{'Content-Type':'application/json'}),...(token()?{Authorization:`Bearer ${token()}`}:{ }),...(options.headers||{})}});
    if(!res.ok) throw new Error(await res.text());
    return await res.json() as T;
  }catch(e){ if('mockFallback' in options) return options.mockFallback as T; throw e; }
}
export const api={baseUrl,get:<T>(p:string,o?:ApiOptions)=>request<T>(p,o),post:<T>(p:string,b?:unknown,o?:ApiOptions)=>request<T>(p,{...o,method:'POST',body:b instanceof FormData?b:JSON.stringify(b||{})}),patch:<T>(p:string,b?:unknown,o?:ApiOptions)=>request<T>(p,{...o,method:'PATCH',body:JSON.stringify(b||{})}),delete:<T>(p:string,o?:ApiOptions)=>request<T>(p,{...o,method:'DELETE'})};

export type HomeOverview={user:{id:number;name:string;email:string};organization:{id:number;name:string;mode?:string}|null;brand:{id:number;name:string;industry?:string;primary_language?:string;setup_status?:string}|null;setup:{completion_percent:number;first_incomplete_step_id:string|null;steps:{id:string;title:string;description:string;status:'done'|'in_progress'|'not_started';estimated_time_minutes?:number;action_label:string;action_href:string}[]};kpis:{id:string;label:string;value:string|number;delta?:string|null;tone?:'neutral'|'good'|'warning';href?:string;helper?:string}[];weekly_activity:{day:string;generated:number;approved:number;published:number}[];pipeline:{status:string;label:string;count:number;href:string;items:{id:number|string;title:string;channel?:string;priority?:string;href:string}[]}[];recent_work:{id:string|number;title:string;type:string;status:string;channel?:string;score?:number|null;updated_at?:string;href:string}[];recommended_action:{title:string;description:string;action_label:string;action_href:string;severity:'info'|'warning'|'success';missing_requirements?:string[]};alerts:{id:string;title:string;description:string;severity:'info'|'warning'|'success'|'danger';href?:string}[];memory_summary?:{title:string;description:string;href:string};channel_health?:{title:string;description:string;status:'good'|'warning'|'missing';href:string};approval_status_summary?:{pending:number;approved:number;total:number}};
export const fetchHomeOverview=()=>api.get<HomeOverview>('/dashboard/home');
