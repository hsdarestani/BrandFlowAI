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

const approvalsFile='app/[locale]/app/approvals/page.tsx';
const approvalsSource=readFileSync(join(root,approvalsFile),'utf8');
const approvalRegressions=[
 '<span className="badge">Approvals</span>',
 '<option value="all">All</option>',
 '<option value="all">All channels</option>',
 '<option value="newest">Newest</option>',
 '<option value="due">Due soon</option>',
 'Reviewer: {selected.reviewer}',
 '>Related Studio draft</Link>',
 '>Related Calendar item</Link>',
 '>Platform preview</b>',
 '>No actions yet.</p>',
 'title={!overview?.channels.telegram_connected ? \'Connect Telegram first\'',
 '>Send via Telegram</button>',
 '>Send via Bale</button>',
 '<Field label="Reviewer name"',
 '<Field label="Reviewer email"',
 '<Field label="Reviewer phone"',
 '<Field label="Due date"',
 'placeholder="Context for the reviewer"',
 '>Delivery method<select',
 '>Public link</option>',
 '>Internal only</option>',
 '>Cancel</button>',
 'use(params)',
];
for(const pattern of approvalRegressions){
 if(approvalsSource.includes(pattern)){
  console.error(`${approvalsFile}: approvals localization/render regression: ${pattern}`);
  failed=true;
 }
}

const toastFile='components/ui/toast.tsx';
const toastSource=readFileSync(join(root,toastFile),'utf8');
if(toastSource.includes('bg-slate-950/90')){
 console.error(`${toastFile}: mobile toast must not regress to the unreadable black treatment`);
 failed=true;
}

if(failed)process.exit(1);
console.log(`Visible localization checks passed across ${sourceFiles.length} source files.`);
