import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env['CI']),
  retries: process.env['CI'] ? 2 : 0,
  reporter: [['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:4200', trace: 'on-first-retry' },
  webServer: { command: 'npm run start', url: 'http://127.0.0.1:4200', reuseExistingServer: !process.env['CI'], timeout: 120000 },
  projects: [
    { name:'chromium-desktop', use:{...devices['Desktop Chrome'], viewport:{width:1365,height:647}} },
    { name:'chromium-compact', use:{...devices['Desktop Chrome'], viewport:{width:680,height:900}} }
  ]
});
