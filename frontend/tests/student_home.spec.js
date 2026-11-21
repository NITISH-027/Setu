import { test, expect } from '@playwright/test';

test('Student home: real saved stats, navigation, search, practice, test resume and offline fallback', async ({ page }) => {
  await page.goto('http://localhost:4173/');
  await page.locator('#student-id-input').fill('stu_e2e_01');
  await page.locator('#student-pin-input').fill('5678');
  const dashboardResponse = page.waitForResponse(r => r.url().includes('/dashboard?'));
  await page.locator('#student-signin-btn').click();
  const data = await (await dashboardResponse).json();
  await expect(page.locator('#continue-learning-btn')).toBeVisible();
  await expect(page.locator('.setu-home-stats > div').nth(1).locator('strong')).toHaveText(String(data.total_attempts));
  await expect(page.locator('.setu-home-streak')).toContainText(`${data.streak_days}-day streak`);
  await page.getByRole('button', { name: 'Chapters', exact: true }).click();
  await page.locator('#chapter-search').fill('fraction');
  await expect(page.locator('.setu-chapter-card').first()).toBeVisible();
  for (const row of await page.locator('.setu-chapter-card').all()) await expect(row).toContainText(/fraction/i);
  await page.locator('#chapter-search').fill('');
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.locator('#continue-learning-btn')).toBeVisible();
    await expect(page.locator('.setu-home-streak')).toBeVisible();
  }
  await page.locator('#continue-learning-btn').click();
  await expect(page.locator('.phone-container')).toBeVisible();
  await page.getByRole('button', { name: '← Learning home', exact: true }).click();
  await page.locator('#home-test-btn').click();
  // A previous test may already be resumable, which is the expected real state.
  await expect(page.locator('.setu-quiz-page')).toBeVisible();
  const start = page.locator('#start-test-btn');
  await expect(page.locator('#start-test-btn, #test-question-text')).toBeVisible();
  if (await start.count()) await start.click();
  await expect(page.locator('#test-question-text')).toBeVisible();
  await page.getByRole('button', { name: 'Save and return to practice', exact: true }).click();
  await page.getByRole('button', { name: '← Learning home', exact: true }).click();
  await expect(page.locator('#home-test-btn')).toHaveText('Continue your test');
  await page.context().setOffline(true);
  await expect(page.locator('.setu-home-error')).toContainText('Offline');
  await expect(page.locator('#home-test-btn')).toBeDisabled();
  await expect(page.locator('.setu-home-stats > div').nth(1).locator('strong')).toHaveText('—');
  await page.locator('#continue-learning-btn').click();
  await expect(page.locator('.phone-container')).toBeVisible();
  await page.context().setOffline(false);
});
