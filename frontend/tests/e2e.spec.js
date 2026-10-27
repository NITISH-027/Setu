import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const screenshotsDir = path.resolve(__dirname, '..', '..', 'screenshots');

test.describe('Mobile Viewport & Phone Layout Tests', () => {

  test('Layout and navigation at 360px viewport', async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 640 });
    await page.goto('http://localhost:4173/');

    // Wait for header and brand elements
    await expect(page.locator('.brand-title')).toBeVisible();
    await expect(page.locator('.nav-tabs')).toBeVisible();

    // Verify document does not have horizontal overflow (scrollWidth <= clientWidth)
    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalOverflow).toBe(false);

    // Capture 360px mobile screenshot
    await page.screenshot({ path: path.join(screenshotsDir, 'mobile_360px.png'), fullPage: true });
  });

  test('Layout and navigation at 390px viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto('http://localhost:4173/');

    // Verify brand and tabs
    await expect(page.locator('.brand-title')).toBeVisible();
    await expect(page.locator('.nav-tabs')).toBeVisible();

    // Check header height is reasonable (not wrapping into broken overlap)
    const headerBox = await page.locator('.app-header').boundingBox();
    expect(headerBox).not.toBeNull();
    expect(headerBox.height).toBeLessThan(120);

    // Verify document does not have horizontal overflow
    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth;
    });
    expect(hasHorizontalOverflow).toBe(false);

    // Capture 390px mobile screenshot
    await page.screenshot({ path: path.join(screenshotsDir, 'mobile_390px.png'), fullPage: true });

    // Switch to Teacher Dashboard and sign in as teacher
    await page.click('text=Teacher Dashboard');
    await expect(page.locator('text=Teacher Sign-In')).toBeVisible();
    await page.fill('#teacher-username-input', 'tea_e2e_8a');
    await page.fill('#teacher-password-input', 'tea_e2e_pass');
    await page.click('#teacher-signin-btn');
    await expect(page.locator('text=Teacher Control Dashboard')).toBeVisible();
    await page.screenshot({ path: path.join(screenshotsDir, 'teacher_dashboard.png'), fullPage: true });

    // Switch to Student App and sign in
    await page.click('text=Student App (Phone)');
    await expect(page.locator('text=Student Sign-In')).toBeVisible();
    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');
    await expect(page.locator('.phone-container')).toBeVisible();
    await expect(page.locator('.info-card')).toBeVisible();
    await page.screenshot({ path: path.join(screenshotsDir, 'student_solve_flow.png'), fullPage: true });
  });

});
