import {existsSync,readdirSync,readFileSync,statSync} from 'node:fs';
import {join,relative,resolve} from 'node:path';

const root=resolve(existsSync('app')?'.':'apps/web');
let failed=false;
const sourceFiles=[];

function walk(directory){
 for(const name of readdirSync(directory)){
  const path=join(directory,name);
  const stat=statSync(path);
  if(stat.isDirectory())walk(path);
  else if(/\.(tsx?|jsx?)$/.test(name))sourceFiles.push(path);
 }
}
for(const directory of ['app','components'])walk(join(root,directory));

const generic=['Production-style demo module','safe mock fallbacks','Lorem ipsum'];
for(const file of sourceFiles){
 const source=readFileSync(file,'utf8');
 for(const text of generic){
  if(source.includes(text)){
   console.error(`${relative(root,file)}: banned visible placeholder: ${text}`);
   failed=true;
  }
 }
}

const localizedFiles={
 'components/signup-screen.tsx':['Workspace onboarding','Your first usable result'],
 'components/login-screen.tsx':['Brand-aware','Approval-ready','Measured'],
};
for(const [fileName,banned] of Object.entries(localizedFiles)){
 const source=readFileSync(join(root,fileName),'utf8');
 for(const visible of banned){
  if(source.includes(`>${visible}<`)||source.includes(`title="${visible}"`)){
   console.error(`${fileName}: untranslated visible text: ${visible}`);
   failed=true;
  }
 }
}

if(failed)process.exit(1);
console.log(`Visible localization checks passed across ${sourceFiles.length} source files.`);
