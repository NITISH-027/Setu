import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const screenshotsDir = path.resolve(__dirname, '..', '..', 'screenshots');

const viewports = [
  { width: 360, height: 640, label: '360px' },
  { width: 390, height: 844, label: '390px' }
];

const tabs = [
  { id: '#tab-student', name: 'Student App', expectedSelector: '#student-signin-btn', shotName: 'student_tab' },
  { id: '#tab-teacher', name: 'Teacher Dashboard', expectedSelector: '#teacher-signin-btn', shotName: 'teacher_tab' },
  { id: '#tab-privacy', name: 'Data & Privacy', expectedSelector: '#privacy-delete-btn', shotName: 'privacy_tab' },
  { id: '#tab-review', name: 'Coverage & Review', expectedSelector: 'text=HARD RULE 5', shotName: 'review_tab' },
  { id: '#tab-paper', name: 'Paper Mode', expectedSelector: 'text=Teacher-Mediated Paper Mode', shotName: 'paper_tab' }
];

test.describe('FIX 7: Rendered Responsive Layout & Tab Overflow Verification', () => {

  for (const vp of viewports) {
    test(`Rendered layout on all 5 tabs at ${vp.label} viewport with zero horizontal overflow`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('http://localhost:4173/');

      await expect(page.locator('.brand-title')).toBeVisible();

      for (const tab of tabs) {
        // Switch tab
        await page.click(tab.id);
        await expect(page.locator(tab.expectedSelector)).toBeVisible();

        // Check horizontal overflow: document.documentElement.scrollWidth <= document.documentElement.clientWidth
        const overflow = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });
        expect(overflow, `Tab ${tab.name} at ${vp.label} has horizontal overflow!`).toBe(false);

        // Capture rendered screenshot
        await page.screenshot({
          path: path.join(screenshotsDir, `layout_${vp.label}_${tab.shotName}.png`),
          fullPage: true
        });
      }
    });
  }

});
