'use client';
export function Tabs({tabs,value,onChange}:{tabs:string[];value:string;onChange:(v:string)=>void}){return <div className="flex flex-wrap gap-2">{tabs.map(x=><button key={x} onClick={()=>onChange(x)} className={value===x?'btn':'chip'}>{x}</button>)}</div>}
