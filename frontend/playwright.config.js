import { defineConfig } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  use: {
    headless: true,
    channel: 'chrome',
    screenshot: 'on',
    viewport: { width: 390, height: 844 }
  },
  webServer: [
    {
      command: 'python -m uvicorn app.main:app --host 127.0.0.1 --port 8000',
      cwd: path.resolve(__dirname, '..', 'backend'),
      port: 8000,
      reuseExistingServer: true,
      timeout: 30000
    },
    {
      command: 'npm run preview -- --port 4173',
      port: 4173,
      reuseExistingServer: true,
      timeout: 30000
    }
  ]
});
