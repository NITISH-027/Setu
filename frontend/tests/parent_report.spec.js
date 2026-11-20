import { test, expect } from '@playwright/test';

test('teacher can preview a private home note, copy it, switch students, and go back', async ({ page, context }, testInfo) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await page.goto('http://localhost:4173');
  await page.locator('#tab-teacher').click();
  await page.locator('#teacher-username-input').fill('tea_e2e_8a');
  await page.locator('#teacher-password-input').fill('tea_e2e_pass');
  await page.locator('#teacher-signin-btn').click();
  await page.getByRole('button', { name: 'Parent report', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Five minutes, together.' })).toBeVisible();
  await expect(page.locator('#report-student option')).not.toHaveCount(0);
  await expect(page.getByText('A next step, not a label.')).toBeVisible();
  await page.locator('#report-student').selectOption(await page.locator('#report-student').inputValue());
  await expect(page.getByText('A next step, not a label.')).toBeVisible();
  await page.getByText('Preview exactly what will be copied or shared').click();
  await expect(page.locator('.report-preview pre')).toContainText('Prototype report');
  await page.getByRole('button', { name: 'Copy for WhatsApp' }).click();
  await expect(page.getByRole('status')).toContainText('Copied.');
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toContain('Setu | Home practice note');
  expect(copied).not.toContain('stu_e2e_');
  expect(copied).not.toContain('8-A');
  const options = await page.locator('#report-student option').evaluateAll(nodes => nodes.map(n => n.value));
  if (options.length > 1) {
    await page.locator('#report-student').selectOption(options[1]);
    await expect(page.locator('.report-paper')).toBeVisible();
  }
  // The report itself must fit a phone even if unrelated legacy header controls do not.
  const bounds = await page.locator('.parent-report').evaluate(el => ({ width: el.scrollWidth, client: el.clientWidth }));
  expect(bounds.width).toBeLessThanOrEqual(bounds.client + 1);
  await page.screenshot({ path: testInfo.outputPath('parent-report-mobile.png'), fullPage: true });
  await page.getByRole('button', { name: 'Back to teacher screen' }).click();
  await expect(page.getByRole('button', { name: 'Parent report', exact: true })).toBeVisible();
});
