import { test, expect } from '@playwright/test';

test('Chapters and progress display saved data without changing the assigned learning path', async ({ page }) => {
  await page.goto('http://localhost:4173');
  await page.locator('#student-id-input').fill('stu_e2e_01');
  await page.locator('#student-pin-input').fill('5678');
  const saved = page.waitForResponse(r => r.url().includes('/dashboard?'));
  await page.locator('#student-signin-btn').click();
  const data = await (await saved).json();
  const writes = [];
  page.on('request', r => { if (['POST','PUT','PATCH','DELETE'].includes(r.method())) writes.push(r.url()); });
  await page.getByRole('button', { name: 'Chapters', exact: true }).click();
  await expect(page.locator('.setu-chapter-card')).toHaveCount(data.concepts.length);
  for (const concept of data.concepts) {
    const card = page.locator('.setu-chapter-card').filter({ has: page.getByRole('heading', { name: concept.name, exact: true }) });
    await expect(card).toContainText(`${concept.attempts} saved answers`);
    await expect(card).toContainText(concept.mastery === null ? 'Not estimated' : `${Math.round(concept.mastery * 100)}%`);
  }
  await page.locator('#chapter-search').fill('fractions');
  await expect(page.locator('.setu-chapter-card').first()).toBeVisible();
  for (const card of await page.locator('.setu-chapter-card').all()) await expect(card).toContainText(/fractions/i);
  await page.locator('#chapter-search').fill('');
  await page.getByRole('button', { name: 'Progress', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Recent concept estimates', exact: true })).toBeVisible();
  await expect(page.locator('.setu-home-concept')).toHaveCount(Math.min(5, data.concepts.length));
  for (const width of [320,390,768,1440]) {
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  expect(writes).toEqual([]);
  await page.getByRole('button', { name: 'Practice', exact: true }).click();
  await expect(page.locator('#question-card')).toBeVisible();
  await expect(page.locator('.practice-aside')).toBeVisible();
  for (const width of [320,390,768,1440]) {
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});
