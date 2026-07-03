export type ApiOptions = RequestInit & { mockFallback?: unknown };
const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
function token(){ if (typeof window === 'undefined') return ''; return localStorage.getItem('brandflow_token') || ''; }
async function request<T>(path:string, options:ApiOptions={}){
  try{
    const res=await fetch(`${baseUrl}${path}`,{...options,headers:{'Content-Type':'application/json',...(token()?{Authorization:`Bearer ${token()}`}:{ }),...(options.headers||{})}});
    if(!res.ok) throw new Error(await res.text());
    return await res.json() as T;
  }catch(e){ if('mockFallback' in options) return options.mockFallback as T; throw e; }
}
export const api={baseUrl,get:<T>(p:string,o?:ApiOptions)=>request<T>(p,o),post:<T>(p:string,b?:unknown,o?:ApiOptions)=>request<T>(p,{...o,method:'POST',body:JSON.stringify(b||{})}),patch:<T>(p:string,b?:unknown,o?:ApiOptions)=>request<T>(p,{...o,method:'PATCH',body:JSON.stringify(b||{})}),delete:<T>(p:string,o?:ApiOptions)=>request<T>(p,{...o,method:'DELETE'})};
