import { test, expect } from '@playwright/test';

async function login(page) {
  await page.goto('http://localhost:4173/');
  await page.locator('#tab-teacher').click();
  await page.locator('#teacher-username-input').fill('tea_e2e_8a');
  await page.locator('#teacher-password-input').fill('tea_e2e_pass');
  const response = page.waitForResponse(r => r.url().endsWith('/api/teacher/class/8-A'));
  await page.locator('#teacher-signin-btn').click();
  const data = await (await response).json();
  await expect(page.locator('.setu-teacher-learner').first()).toBeVisible();
  return data;
}

test('Teacher overview shows server counts and preserves responsive workspace, override and logout', async ({ page }, testInfo) => {
  const data = await login(page);
  const students = new Set([...Object.values(data.grouped_by_gap).flat(), ...data.undecided_students].map(s => s.student_id));
  const stats = page.locator('.setu-home-stats > div strong');
  await expect(stats.nth(0)).toHaveText(String(students.size));
  await expect(stats.nth(2)).toHaveText(String(data.total_decisions));
  await expect(stats.nth(3)).toHaveText(String(data.total_overrides));
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.getByRole('button', { name: 'Log out', exact: true })).toBeVisible();
  }
  await page.locator('[data-testid^="override-btn-"]').first().click();
  await page.locator('#apply-override-btn').click();
  await expect(page.locator('#override-error-msg')).toContainText('mandatory');
  await page.setViewportSize({ width: 390, height: 844 });
  const bounds = await page.locator('.setu-teacher-modal > div').boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(391);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(845);
  await page.screenshot({ path: testInfo.outputPath('teacher-override-mobile.png') });
  await page.locator('#override-reason-input').fill('Local regression: teacher reviewed this learning evidence.');
  const applied = page.waitForResponse(r => r.url().endsWith('/api/teacher/override') && r.request().method() === 'POST');
  await page.locator('#apply-override-btn').click();
  expect((await applied).status()).toBe(200);
  await expect(page.locator('.setu-teacher-modal')).toHaveCount(0);
  await expect(page.getByText(/Override successfully applied/)).toBeVisible();
  await page.getByRole('button', { name: 'Log out', exact: true }).click();
  await expect(page.locator('#teacher-signin-btn')).toBeVisible();
  await expect(page.locator('.setu-teacher')).toHaveCount(0);
});

test('Denied class switch clears private overview and ignores a late previous-class response', async ({ page }) => {
  await login(page);
  let release;
  const held = new Promise(resolve => { release = resolve; });
  let started;
  const requested = new Promise(resolve => { started = resolve; });
  await page.route('**/api/teacher/class/8-A', async route => {
    const response = await route.fetch();
    started();
    await held;
    await route.fulfill({ response });
  });
  await page.getByRole('button', { name: 'Refresh', exact: true }).click();
  await requested;
  await page.locator('#class-selector').selectOption('8-B');
  await expect(page.getByText('Error:', { exact: true })).toBeVisible();
  release();
  await page.waitForTimeout(200);
  await expect(page.locator('.setu-teacher-learner')).toHaveCount(0);
  for (const stat of await page.locator('.setu-home-stats > div strong').all()) await expect(stat).toHaveText('—');
  await expect(page.locator('#attention-summary-panel')).toContainText('loading or unavailable');
  await expect(page.locator('.teacher-attention-row')).toHaveCount(0);
  await expect(page.locator('[data-testid^="override-btn-"]')).toHaveCount(0);
  await expect(page.locator('.setu-home-continue')).toContainText('loading or unavailable');
});

test('Question authoring keeps save, draft labels and edit flow on the real API', async ({ page }) => {
  await login(page);
  const form = page.locator('.setu-authoring');
  const concept = form.getByRole('combobox', { name: 'Concept', exact: true });
  await expect(concept.locator('option').nth(1)).toBeAttached();
  const value = await concept.locator('option').nth(1).getAttribute('value');
  await concept.selectOption(value);
  await form.getByLabel('Question', { exact: true }).fill('Local UI regression: what is 2 + 2?');
  await form.getByLabel('Mark option 1 as correct').check();
  for (let i = 1; i <= 4; i++) await form.getByLabel(`Option ${i}`, { exact: true }).fill(String(i + 3));
  for (const input of await form.getByLabel('Misconception tag', { exact: true }).all()) await input.fill('tag_sign_error');
  const saved = page.waitForResponse(r => r.url().endsWith('/api/teacher/authoring/questions') && r.request().method() === 'POST');
  await form.getByRole('button', { name: 'Save as draft', exact: true }).click();
  expect((await saved).status()).toBe(200);
  await expect(form.getByRole('status')).toContainText('UNREVIEWED DRAFT');
  const draft = form.locator('.teacher-draft-list article').filter({ hasText: 'Local UI regression' });
  await draft.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(form.getByLabel('Question', { exact: true })).toHaveValue('Local UI regression: what is 2 + 2?');
  await expect(form.getByRole('status')).toContainText('re-enter the options');
  await form.getByRole('button', { name: 'Cancel edit', exact: true }).click();
  await expect(form.getByLabel('Question', { exact: true })).toHaveValue('');
});
