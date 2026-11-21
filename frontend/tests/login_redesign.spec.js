import { test, expect } from '@playwright/test';

const home = 'http://localhost:4173/';

test.describe('Lilac login redesign', () => {
  for (const width of [320, 390, 768, 1440]) {
    test(`Login fits ${width}px and keeps both roles available`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(home);
      await expect(page.locator('.setu-login-card')).toBeVisible();
      await expect(page.locator('#tab-student')).toHaveAttribute('aria-pressed', 'true');
      await expect(page.locator('#tab-teacher')).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const art = page.locator('.setu-login-art');
      await expect(art).toBeVisible();
      expect(await art.evaluate(el => getComputedStyle(el).backgroundImage)).toContain('setu-login-art');
    });
  }

  test('PIN visibility can be toggled without losing the value', async ({ page }) => {
    await page.goto(home);
    await page.locator('#student-pin-input').fill('5678');
    await page.getByRole('button', { name: 'Show 4-digit PIN', exact: true }).click();
    await expect(page.locator('#student-pin-input')).toHaveAttribute('type', 'text');
    await expect(page.locator('#student-pin-input')).toHaveValue('5678');
    await page.getByRole('button', { name: 'Hide 4-digit PIN', exact: true }).click();
    await expect(page.locator('#student-pin-input')).toHaveAttribute('type', 'password');
  });

  test('Teacher retains username/password fields and real demo-off error', async ({ page }) => {
    await page.goto(home);
    await page.locator('#tab-teacher').click();
    await expect(page.locator('#teacher-username-input')).toBeVisible();
    await expect(page.locator('#teacher-password-input')).toHaveAttribute('type', 'password');
    await page.locator('#teacher-demo-btn').click();
    await expect(page.getByRole('alert')).toContainText('Demo mode is off');
    await page.locator('#tab-student').click();
    await expect(page.locator('#student-id-input')).toBeVisible();
  });

  test('Student demo picker stays hidden when backend demo mode is off', async ({ page }) => {
    await page.goto(home);
    await expect(page.locator('.setu-login-card')).toBeVisible();
    await expect(page.locator('#demo-student-picker')).toHaveCount(0);
  });
});

for (const width of [320,390,1440]) test(`Student demo entry is expanded, empty-aware and retryable at ${width}px`, async ({page}) => {
  await page.setViewportSize({width,height:900});
  let mode = 'empty';
  await page.route('**/api/auth/demo-students', route => {
    if (mode === 'error') return route.fulfill({status:503,json:{detail:'Temporarily unavailable'}});
    if (mode === 'off') return route.fulfill({status:403,json:{detail:'Demo mode is disabled'}});
    return route.fulfill({json:{students:mode === 'ready' ? [{student_id:'stu_demo_01',class_id:'8-A'}] : []}});
  });
  await page.goto(home);
  await expect(page.getByTestId('student-demo-notice')).toContainText('database has no student profiles');
  await page.screenshot({path:`/downloads/setu-demo-empty-${width}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  mode='error';
  await page.getByRole('button',{name:'Retry student demos'}).click();
  await expect(page.getByTestId('student-demo-notice')).toContainText('could not be loaded');
  mode='ready';
  await page.getByRole('button',{name:'Retry student demos'}).click();
  await expect(page.getByTestId('demo-login-stu_demo_01')).toBeVisible();
  await expect(page.locator('#demo-student-picker details')).toHaveCount(0);
  await page.screenshot({path:`/downloads/setu-demo-ready-${width}.png`,fullPage:true});
  mode='off';
  await page.reload();
  await expect(page.locator('.setu-login-card')).toBeVisible();
  await expect(page.getByTestId('student-demo-notice')).toHaveCount(0);
  await expect(page.locator('#demo-student-picker')).toHaveCount(0);
});
