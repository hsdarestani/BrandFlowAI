'use client';

import {createContext, useContext, useRef, useState} from 'react';

type ToastItem = {id:number; message:string};
const ToastContext = createContext<(message:string)=>void>(()=>{});

export function ToastProvider({children}:{children:React.ReactNode}) {
  const [items,setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const push = (message:string) => {
    const text = String(message || '').trim();
    if (!text) return;
    const id = nextId.current++;
    setItems(current => [...current,{id,message:text}]);
    window.setTimeout(() => {
      setItems(current => current.filter(item => item.id !== id));
    },3200);
  };

  return <ToastContext.Provider value={push}>
    {children}
    <div
      aria-live="polite"
      aria-atomic="true"
      className="pointer-events-none fixed inset-x-3 bottom-[calc(5.75rem+env(safe-area-inset-bottom))] z-[90] flex flex-col items-center gap-2 xl:inset-x-auto xl:bottom-4 xl:end-4 xl:items-end"
    >
      {items.map(item => <div
        key={item.id}
        role="status"
        className="pointer-events-auto w-full max-w-sm rounded-2xl border border-slate-200 bg-white/95 px-4 py-3 text-sm font-bold text-slate-900 shadow-xl shadow-slate-900/10 backdrop-blur"
      >
        {item.message}
      </div>)}
    </div>
  </ToastContext.Provider>;
}

export const useToast = () => useContext(ToastContext);
