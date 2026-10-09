import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'tests',testMatch:'ui.spec.ts',use:{channel:'msedge',viewport:{width:1440,height:1000}},webServer:{command:'npm run dev',url:'http://127.0.0.1:43191',reuseExistingServer:false}});
