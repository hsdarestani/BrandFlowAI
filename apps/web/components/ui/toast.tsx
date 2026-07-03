'use client';
import {createContext,useContext,useState} from 'react';
const C=createContext<(m:string)=>void>(()=>{});
export function ToastProvider({children}:{children:React.ReactNode}){const [items,set]=useState<string[]>([]);const push=(m:string)=>{set(x=>[...x,m]);setTimeout(()=>set(x=>x.slice(1)),3000)};return <C.Provider value={push}>{children}<div className="fixed bottom-4 end-4 z-50 space-y-2">{items.map((m,i)=><div key={i} className="rounded-2xl border border-cyan-400/30 bg-slate-950/90 px-4 py-3 shadow-2xl backdrop-blur">{m}</div>)}</div></C.Provider>}
export const useToast=()=>useContext(C);
