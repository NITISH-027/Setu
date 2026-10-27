import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  use: {
    headless: true,
    channel: 'chrome',
    screenshot: 'on',
    viewport: { width: 390, height: 844 }
  },
  webServer: {
    command: 'npm run preview -- --port 4173',
    port: 4173,
    reuseExistingServer: true,
    timeout: 15000
  }
});
