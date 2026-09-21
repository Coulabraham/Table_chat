import { defineConfig, devices } from '@playwright/test'
export default defineConfig({testDir:'./e2e',workers:1,use:{baseURL:process.env.TABLECHAT_URL||'https://localhost',ignoreHTTPSErrors:true,trace:'retain-on-failure'},projects:[{name:'desktop',use:{...devices['Desktop Chrome']}},{name:'mobile',use:{...devices['iPhone 13'],browserName:'chromium'}}]})
