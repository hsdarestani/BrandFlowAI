import {defineConfig,devices} from '@playwright/test';

export default defineConfig({
 testDir:'./e2e',
 fullyParallel:false,
 workers:1,
 retries:1,
 timeout:60_000,
 expect:{timeout:12_000},
 reporter:[['list'],['html',{outputFolder:'playwright-report',open:'never'}]],
 use:{
  baseURL:process.env.E2E_WEB_URL||'http://127.0.0.1:3000',
  trace:'retain-on-failure',
  screenshot:'only-on-failure',
  video:'retain-on-failure',
 },
 projects:[{name:'chromium',use:{...devices['Desktop Chrome']}}],
 outputDir:'test-results',
});
