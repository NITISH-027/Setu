import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const pack = JSON.parse(fs.readFileSync(path.join(root, 'packs/cbse_math_pack.json'), 'utf8'));
const home = 'http://localhost:4173/';

async function enterTest(page) {
  await page.goto(home);
  await page.locator('#student-id-input').fill('stu_e2e_01');
  await page.locator('#student-pin-input').fill('5678');
  await page.locator('#student-signin-btn').click();
  await page.locator('#continue-learning-btn').click();
  await page.getByRole('button', { name: /Take Chapter Test/ }).click();
}

function optionFor(state, correct) {
  return pack.questions.find(question => question.id === state.current_item.question.id).options.find(option => option.is_correct === correct);
}

async function answer(page, state, correct) {
  const option = optionFor(state, correct);
  await page.locator(`[data-testid="test-option-${option.id}"]`).click();
  const response = page.waitForResponse(r => r.url().endsWith('/test/answer'));
  await page.locator('#submit-test-answer').click();
  const data = await (await response).json();
  return data.session || data;
}

test('Adaptive lilac quiz: score, review, resume, lost-response retry and report', async ({ page }) => {
  // Dedicated test DB only, using the same safety-checked seeder as the test server.
  execFileSync('python', [path.join(root, 'scripts/seed_e2e_fixtures.py')], {
    cwd: path.join(root, 'backend'),
    env: { ...process.env, SETU_TEST_ENV: '1', DATABASE_URL: 'sqlite:///./setu_test.db' }
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  await enterTest(page);
  await expect(page.locator('#start-test-btn')).toBeVisible();
  const startResponse = page.waitForResponse(r => r.url().endsWith('/test/start'));
  await page.locator('#start-test-btn').click();
  let state = await (await startResponse).json();
  const sessionId = state.session_id;
  await expect(page.locator('[data-testid="quiz-status-2"]')).toBeDisabled();
  await expect(page.locator('#submit-test-answer')).toBeDisabled();
  state = await answer(page, state, true);
  await expect(page.locator('.setu-quiz-score strong')).toHaveText('100%');
  await expect(page.locator('[data-testid="quiz-status-1"]')).toHaveAttribute('aria-label', /correct, review/);

  // The server accepts an answer but its response is lost. Retry must not grade twice.
  let drop = true;
  await page.route('**/test/answer', async route => {
    if (drop) { drop = false; await route.fetch(); await route.abort('failed'); }
    else await route.continue();
  });
  const wrong = optionFor(state, false);
  await page.locator(`[data-testid="test-option-${wrong.id}"]`).click();
  await page.locator('#submit-test-answer').click();
  await expect(page.getByRole('alert')).toBeVisible();
  await expect(page.locator(`[data-testid="test-option-${wrong.id}"]`)).toHaveAttribute('aria-pressed', 'true');
  const retryResponse = page.waitForResponse(r => r.url().endsWith('/test/answer'));
  await page.locator('#submit-test-answer').click();
  state = await (await retryResponse).json();
  expect(state.idempotent_replay).toBe(true);
  expect(state.answered_count).toBe(2);
  expect(state.answered_items).toHaveLength(2);
  await page.unroute('**/test/answer');
  await expect(page.locator('.setu-quiz-score strong')).toHaveText('50%');
  const meter = await page.getByRole('progressbar').evaluate(el => ({
    expected: Number(el.getAttribute('aria-valuenow')),
    actual: el.firstElementChild.getBoundingClientRect().width / el.getBoundingClientRect().width * 100
  }));
  expect(Math.abs(meter.actual - meter.expected)).toBeLessThan(0.5);


  await page.locator('[data-testid="quiz-status-1"]').click();
  await expect(page.locator('.setu-quiz-topic')).toContainText('read-only');
  for (const button of await page.locator('.setu-quiz-option').all()) await expect(button).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Previous', exact: true })).toBeDisabled();
  await page.locator('[data-testid="quiz-status-3"]').click();
  await expect(page.locator('#submit-test-answer')).toBeDisabled();

  // Re-entering after reload gets persisted status, not a new test or local-only guesses.
  await enterTest(page);
  await expect(page.locator('[data-testid="quiz-status-3"]')).toHaveAttribute('aria-current', 'step');
  await expect(page.locator('.setu-quiz-score strong')).toHaveText('50%');
  for (const width of [320, 390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.locator('#submit-test-answer')).toBeVisible();
  }
  while (state.current_item) state = await answer(page, state, true);
  expect(state.session_id).toBe(sessionId);
  expect(state.answered_items.length).toBe(state.summary.total_served);
  await expect(page.locator('#test-score')).toHaveText(`${state.summary.total_correct} / ${state.summary.total_served} correct`);
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '100');
  expect(await page.getByRole('progressbar').evaluate(el => Math.abs(el.firstElementChild.getBoundingClientRect().width - el.getBoundingClientRect().width))).toBeLessThan(1);
  await page.locator('[data-testid="quiz-status-1"]').click();
  await expect(page.locator('.setu-quiz-topic')).toContainText('read-only');
  await page.locator(`[data-testid="quiz-status-${state.answered_count}"]`).click();
  await page.getByRole('button', { name: 'Back to report', exact: true }).click();
  await expect(page.locator('#test-score')).toBeVisible();
  await page.locator('#practice-weakest-btn').click();
  await expect(page.locator('.phone-container')).toBeVisible();
  expect(pageErrors).toEqual([]);
});
