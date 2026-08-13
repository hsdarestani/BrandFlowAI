import {spawn} from 'node:child_process';
import {setTimeout as sleep} from 'node:timers/promises';

const port=3100;
const base=`http://127.0.0.1:${port}`;
const nextBin='node_modules/next/dist/bin/next';
let output='';

const server=spawn(process.execPath,[nextBin,'start','-p',String(port)],{
  cwd:process.cwd(),
  env:{...process.env,PORT:String(port)},
  stdio:['ignore','pipe','pipe'],
});

server.stdout.on('data',chunk=>{output+=String(chunk);});
server.stderr.on('data',chunk=>{output+=String(chunk);});

let stopped=false;
server.on('exit',()=>{stopped=true;});

async function stop(){
  if(!stopped){
    server.kill('SIGTERM');
    await Promise.race([new Promise(resolve=>server.once('exit',resolve)),sleep(3000)]);
  }
}

async function waitUntilReady(){
  for(let attempt=1;attempt<=40;attempt++){
    if(stopped)throw new Error(`Next.js exited before smoke tests.\n${output}`);
    try{
      const response=await fetch(`${base}/fa`,{redirect:'manual'});
      if(response.status<500)return;
    }catch{}
    await sleep(500);
  }
  throw new Error(`Next.js did not become ready for runtime smoke tests.\n${output}`);
}

async function checkRoute(route){
  const response=await fetch(`${base}${route}`,{redirect:'manual'});
  const body=await response.text();
  if(response.status>=500){
    throw new Error(`${route} returned HTTP ${response.status}.\n${body.slice(0,1200)}\n${output}`);
  }
  if(/Application error:\s*a server-side exception/i.test(body)){
    throw new Error(`${route} rendered the Next.js server-side exception page.\n${body.slice(0,1200)}\n${output}`);
  }
  console.log(`Runtime render OK: ${route} (${response.status})`);
}

try{
  await waitUntilReady();
  for(const route of ['/fa/app/approvals','/en/app/approvals','/de/app/approvals','/fa/app/calendar']){
    await checkRoute(route);
  }
  console.log('Critical localized runtime render smoke checks passed.');
}finally{
  await stop();
}
