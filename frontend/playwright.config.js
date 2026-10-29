import { defineConfig } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: './tests',
  globalSetup: './tests/global_setup.js',
  workers: 1,
  timeout: 60000,
  use: {
    headless: true,
    channel: 'chrome',
    screenshot: 'on',
    viewport: { width: 390, height: 844 }
  },
  webServer: [
    {
      command: 'python ../scripts/run_e2e_server.py',
      cwd: path.resolve(__dirname, '..', 'backend'),
      port: 8000,
      reuseExistingServer: false,
      timeout: 30000
    },
    {
      command: 'npm run preview -- --port 4173',
      port: 4173,
      reuseExistingServer: false,
      timeout: 30000
    }
  ]
});
