import {execSync} from 'node:child_process';
import {existsSync} from 'node:fs';
const root=existsSync('app')?'.':'apps/web';
const pattern='Production-style demo module|safe mock fallbacks|Lorem ipsum';
try{const out=execSync(`rg -n "${pattern}" ${root}/app ${root}/components`,{encoding:'utf8'});console.error(out);process.exit(1)}catch(e){if(e.status===1){console.log('No banned visible placeholder strings found.')}else throw e}
