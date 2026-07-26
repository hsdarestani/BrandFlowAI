import {execSync} from 'node:child_process';
import {existsSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';

const root=existsSync('app')?'.':'apps/web';
const genericPattern='Production-style demo module|safe mock fallbacks|Lorem ipsum';
let failed=false;
try{
 const out=execSync(`rg -n "${genericPattern}" ${root}/app ${root}/components`,{encoding:'utf8'});
 console.error(out);
 failed=true;
}catch(error){
 if(error.status!==1)throw error;
}

const localizedFiles={
 'components/signup-screen.tsx':['Workspace onboarding','Your first usable result','First week'],
 'components/login-screen.tsx':['Brand-aware','Approval-ready','Measured'],
};
for(const [relative,banned] of Object.entries(localizedFiles)){
 const file=resolve(root,relative);
 const source=readFileSync(file,'utf8');
 for(const visible of banned){
  if(source.includes(`>${visible}<`)||source.includes(`title="${visible}"`)){
   console.error(`${relative}: untranslated visible text: ${visible}`);
   failed=true;
  }
 }
}

if(failed)process.exit(1);
console.log('Visible placeholder and localization regression checks passed.');
