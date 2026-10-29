import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const screenshotsDir = path.resolve(__dirname, '..', '..', 'screenshots');

test.describe('Setu Full Acceptance Browser Journeys (Tests A - L)', () => {

  test('Acceptance Test A: Full Learning Journey on Student Screen', async ({ page }) => {
    // 1. Visit app
    await page.goto('http://localhost:4173/');

    // 2. Sign in as student
    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');

    // 3. Initial Solve stage
    await expect(page.locator('.badge-stage')).toHaveText('solve', { timeout: 10000 });
    await expect(page.locator('#stage-change-message')).toBeVisible();

    // Answer wrong with misconception (select option 2)
    const opt2 = page.locator('.option-btn').nth(1);
    await opt2.click();
    await page.click('#submit-attempt-btn');

    // 4. Diagnostic Probe stage
    await expect(page.locator('.badge-stage')).toHaveText('probe', { timeout: 10000 });
    await expect(page.locator('#stage-change-message')).toContainText('Diagnostic Probe');

    // Answer wrong on probe
    const probeOptWrong = page.locator('.option-btn').last();
    await probeOptWrong.click();
    await page.click('#submit-attempt-btn');

    // If second probe appears, answer it; else lesson screen appears
    await page.waitForTimeout(1000);
    const currentBadge = await page.locator('.badge-stage').textContent();
    if (currentBadge === 'probe') {
      const probe2Opt = page.locator('.option-btn').last();
      await probe2Opt.click();
      await page.click('#submit-attempt-btn');
    }

    // 5. Micro-Lesson Screen Reached!
    await expect(page.locator('#lesson-screen')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#lesson-title')).toBeVisible();
    await expect(page.locator('#lesson-content')).toBeVisible();
    await expect(page.locator('#continue-lesson-btn')).toBeVisible();

    // Screenshot of Lesson Screen
    await page.screenshot({ path: path.join(screenshotsDir, 'lesson_screen.png') });

    // Click "Continue" to explicitly transition to Bridge Re-check
    await page.click('#continue-lesson-btn');

    // 6. Bridge Re-Check stage
    await expect(page.locator('.badge-stage')).toHaveText('bridge_recheck', { timeout: 10000 });
    await expect(page.locator('#stage-change-message')).toContainText('Bridge Re-check');

    // Answer correctly (option 1 is correct for integers probe/recheck)
    const correctOpt = page.locator('.option-btn').first();
    await correctOpt.click();
    await page.click('#submit-attempt-btn');

    // 7. Returned to original topic in solve stage!
    await expect(page.locator('.badge-stage')).toHaveText('solve', { timeout: 10000 });
    await expect(page.locator('#stage-change-message')).toContainText('Returned to original topic');
  });

  test('Acceptance Test D & C: Stuck Flag Screen and Teacher Override Release', async ({ page }) => {
    await page.goto('http://localhost:4173/');

    // Sign in as student 2
    await page.fill('#student-id-input', 'stu_e2e_02');
    await page.fill('#student-pin-input', '9876');
    await page.click('#student-signin-btn');

    await expect(page.locator('.badge-stage')).toHaveText('solve', { timeout: 10000 });

    // Wrong answer 1 -> probe
    await page.locator('.option-btn').nth(1).click();
    await page.click('#submit-attempt-btn');
    await expect(page.locator('.badge-stage')).toHaveText('probe', { timeout: 10000 });

    // Answer probe correctly -> contradicts gap, returns to solve
    await page.locator('.option-btn').first().click();
    await page.click('#submit-attempt-btn');
    await expect(page.locator('.badge-stage')).toHaveText('solve', { timeout: 10000 });

    // Wrong answer 2 in solve -> 2nd consecutive wrong solve answer -> Teacher flag!
    await page.locator('.option-btn').nth(1).click();
    await page.click('#submit-attempt-btn');

    // Teacher flag screen is displayed
    await expect(page.locator('#teacher-flag-screen')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#teacher-flag-message')).toContainText('Your teacher has been notified');

    // Screenshot of Flag Screen
    await page.screenshot({ path: path.join(screenshotsDir, 'flag_screen.png') });

    // Switch to Teacher tab to release student
    await page.click('#tab-teacher');
    await page.fill('#teacher-username-input', 'tea_e2e_8a');
    await page.fill('#teacher-password-input', 'tea_e2e_pass');
    const [loginRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/auth/login')),
      page.click('#teacher-signin-btn')
    ]);
    expect(loginRes.ok()).toBeTruthy();

    // Override student stu_e2e_02 specifically
    const overrideBtnStu2 = page.locator('[data-testid="override-btn-stu_e2e_02"]');
    await expect(overrideBtnStu2).toBeVisible({ timeout: 10000 });
    await overrideBtnStu2.click();

    // Verify short reason (< 3 chars) shows validation message instead of crashing
    await page.fill('#override-reason-input', 'ok');
    await page.click('#apply-override-btn');
    await expect(page.locator('#override-error-msg')).toBeVisible();
    await expect(page.locator('#override-error-msg')).toContainText('at least 3 characters');

    // Now submit with valid pedagogical reason
    await page.fill('#override-reason-input', 'Released student after 1-on-1 clinic support');
    await page.click('#apply-override-btn');
    await expect(page.locator('#override-reason-input')).not.toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Override successfully applied')).toBeVisible({ timeout: 10000 });

    // Switch back to student -> Sign in again to verify student is released!
    await page.click('#tab-student');
    await page.fill('#student-id-input', 'stu_e2e_02');
    await page.fill('#student-pin-input', '9876');
    await page.click('#student-signin-btn');
    await expect(page.locator('.option-btn').first()).toBeVisible({ timeout: 10000 });
  });

  test('Acceptance Test F: Fast Learner Move-Ahead Screen', async ({ page }) => {
    await page.goto('http://localhost:4173/');

    // Sign in as fast learner (consecutive_successes = 2, mastery = 0.90)
    await page.fill('#student-id-input', 'stu_e2e_fast');
    await page.fill('#student-pin-input', '2222');
    await page.click('#student-signin-btn');

    await expect(page.locator('.badge-stage')).toHaveText('solve', { timeout: 10000 });

    // Answer 3rd consecutive correct answer
    await page.locator('.option-btn').first().click();
    await page.click('#submit-attempt-btn');

    // Enrichment / Move-ahead screen displayed!
    await expect(page.locator('#enrichment-screen')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#move-ahead-message')).toBeVisible();

    // Screenshot of Enrichment Screen
    await page.screenshot({ path: path.join(screenshotsDir, 'enrichment_screen.png') });
  });

  test('Acceptance Test H: Teacher Paper Mode Bulk Entry Form', async ({ page }) => {
    await page.goto('http://localhost:4173/');

    await page.click('#tab-paper');

    // Login as teacher on paper tab
    await page.fill('#teacher-paper-username', 'tea_e2e_8a');
    await page.fill('#teacher-paper-password', 'tea_e2e_pass');
    await page.click('button:has-text("Sign In")');

    // Form inputs are populated
    await page.fill('#bulk-student-id-0', 'stu_e2e_01');
    await page.fill('#bulk-question-id-0', 'q_c8_leq_01');
    await page.fill('#bulk-option-id-0', 'opt_1');

    // Add bad question ID row
    await page.click('button:has-text("+ Add Student Row")');
    await page.fill('#bulk-student-id-2', 'stu_e2e_01');
    await page.fill('#bulk-question-id-2', 'bad_q_nonexistent');
    await page.fill('#bulk-option-id-2', 'opt_1');

    // Process bulk submit
    await page.click('#process-bulk-paper-btn');

    // Server confirmed success for valid rows
    await expect(page.locator('#bulk-paper-success')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#bulk-paper-success')).toContainText('Server Confirmed: Processed');

    // Structured errors for bad question
    await expect(page.locator('#bulk-paper-errors')).toBeVisible();
    await expect(page.locator('#bulk-paper-errors')).toContainText('bad_q_nonexistent');

    // Screenshot of Paper Entry Screen
    await page.screenshot({ path: path.join(screenshotsDir, 'paper_entry_screen.png') });
  });

  test('Acceptance Test K: Student Data Export in Privacy View', async ({ page }) => {
    await page.goto('http://localhost:4173/');

    await page.click('#tab-privacy');

    // Login as teacher
    await page.fill('input[placeholder="Username"]', 'tea_e2e_8a');
    await page.fill('input[placeholder="Password"]', 'tea_e2e_pass');
    const [loginRes] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/api/auth/login')),
      page.click('button:has-text("Sign In")')
    ]);
    expect(loginRes.ok()).toBeTruthy();

    // Export student data
    await page.fill('#export-student-id-input', 'stu_e2e_01');
    await page.click('#export-student-btn');

    // JSON output is displayed without secrets
    await expect(page.locator('#export-json-output')).toBeVisible({ timeout: 10000 });
    const jsonText = await page.locator('#export-json-output').textContent();
    expect(jsonText).toContain('stu_e2e_01');
    expect(jsonText).not.toContain('pin_hash');
    expect(jsonText).not.toContain('salt');
    expect(jsonText).not.toContain('subject_key');
  });

  test('Acceptance Test L: Content Editor Schema Validator in Review View', async ({ page }) => {
    const packPath = path.resolve(__dirname, '..', '..', 'packs', 'cbse_math_pack.json');
    const originalPackContent = fs.readFileSync(packPath, 'utf-8');

    try {
      await page.goto('http://localhost:4173/');

      await page.click('#tab-review');

      // Sign in as reviewer
      await page.fill('input[placeholder="Reviewer Username"]', 'rev_e2e_01');
      await page.fill('input[placeholder="Password"]', 'rev_e2e_pass');
      await page.click('button:has-text("Sign In")');

      // Content Editor section is visible
      await expect(page.locator('#editor-item-select')).toBeVisible({ timeout: 10000 });

      // 1. Submit invalid edit (break options to have 0 correct options)
      const invalidJson = JSON.stringify({
        id: 'q_c8_leq_08',
        question_text: 'Invalid edit test question',
        options: [
          { id: 'opt_1', text: '5', is_correct: false, misconception_tag: 'tag1' },
          { id: 'opt_2', text: '10', is_correct: false, misconception_tag: 'tag2' }
        ]
      }, null, 2);

      await page.fill('#editor-item-textarea', invalidJson);
      await page.click('#save-editor-item-btn');

      // Rejection error displayed
      await expect(page.locator('#editor-error-message')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('#editor-error-message')).toContainText('exactly one correct option');

      // 2. Submit valid edit
      const validJson = JSON.stringify({
        id: 'q_c8_leq_08',
        concept: 'c8_math_linear_eq_one_var',
        difficulty: 0.7,
        question_text: 'Solve for k: 7k - 2 = 5k + 8 (Reviewed version)',
        options: [
          { id: 'opt_1', text: 'k = 5', is_correct: true },
          { id: 'opt_2', text: 'k = 3', is_correct: false, misconception_tag: 'tag_sign_error_on_transposition' }
        ]
      }, null, 2);

      await page.fill('#editor-item-textarea', validJson);
      await page.click('#save-editor-item-btn');

      // Success message displayed: status reset to author-drafted, unreviewed
      await expect(page.locator('#editor-success-message')).toBeVisible({ timeout: 10000 });
      await expect(page.locator('#editor-success-message')).toContainText('author-drafted, unreviewed');
    } finally {
      fs.writeFileSync(packPath, originalPackContent, 'utf-8');
    }
  });

});
