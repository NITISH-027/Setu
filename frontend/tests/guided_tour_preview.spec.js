import { test, expect } from '@playwright/test';

test.describe('Guided Tour Step 5 Interactive Previews & Fixes', () => {
  const viewports = [
    { name: 'desktop', width: 1280, height: 800 },
    { name: 'mobile-390', width: 390, height: 844 },
    { name: 'mobile-360', width: 360, height: 740 },
  ];

  for (const vp of viewports) {
    test(`Verification at viewport ${vp.name} (${vp.width}x${vp.height})`, async ({ page }) => {
      const consoleErrors = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('http://localhost:4173');

      // Check overflow on landing
      const bodyOverflow = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
      expect(bodyOverflow).toBe(true);

      // Open Guided Tour
      const tourBtn = page.locator('#guided-tour-btn');
      await expect(tourBtn).toBeVisible();
      await tourBtn.click();

      // Step 1: Check title
      const modalTitle = page.locator('#tour-modal-title');
      await expect(modalTitle).toContainText('What Setu Solves');

      // Next to Step 2
      await page.getByRole('button', { name: 'Next →' }).click();
      await expect(modalTitle).toContainText('One Student Learning Journey');
      // FIX 5 Check 1: "When probe evidence supports a gap"
      const beat3 = page.locator('.tour-beats-list');
      await expect(beat3).toContainText('When probe evidence supports a gap');
      await expect(beat3).not.toContainText('When probe evidence confirms a gap');

      // Next to Step 3
      await page.getByRole('button', { name: 'Next →' }).click();
      await expect(modalTitle).toContainText('Teacher Intervention & Command');

      // Next to Step 4
      await page.getByRole('button', { name: 'Next →' }).click();
      await expect(modalTitle).toContainText('Offline & Paper Support');
      // FIX 5 Check 2: Worksheet notice
      const step4Text = page.locator('.tour-body');
      await expect(step4Text).toContainText(
        'Worksheet printing is not available in this build; teachers can still enter answers from paper practice in the Paper Mode tab.'
      );
      await expect(step4Text).not.toContainText('currently undergoing verification');

      // Next to Step 5
      await page.getByRole('button', { name: 'Next →' }).click();
      await expect(modalTitle).toContainText('Explore Interactive Previews');

      // FIX 1: Verify NO credentials (passwords, PINs, IDs) displayed anywhere
      const step5Text = await page.locator('.tour-body').innerText();
      expect(step5Text).not.toContain('teacher123');
      expect(step5Text).not.toContain('PIN:');
      expect(step5Text).not.toContain('1234');

      // FIX 2: Test Interactive Student Preview
      const openStudentBtn = page.getByRole('button', { name: 'Open Student App' });
      await expect(openStudentBtn).toBeVisible();
      await openStudentBtn.click();

      // Screen 1: Persistent banner check
      const studentBanner = page.locator('.preview-persistent-banner');
      await expect(studentBanner).toBeVisible();
      await expect(studentBanner).toContainText(
        'Prepared preview - illustrates the real student flow. Not connected to the live engine or real student data.'
      );

      // Stage 1: Solve for x: x + 7 = 14
      await expect(page.locator('.preview-card')).toContainText('Solve for x: x + 7 = 14');
      // Click option B: 21 (wrong answer)
      await page.getByRole('button', { name: 'B) 21' }).click();
      await expect(page.locator('.preview-feedback-box')).toContainText('Incorrect');
      await page.getByRole('button', { name: 'Continue to Diagnostic Gap Check →' }).click();

      // Screen 2: Hypothesis card check
      await expect(studentBanner).toBeVisible();
      await expect(page.locator('.preview-card')).toContainText('Possible prerequisite gap detected');
      await page.getByRole('button', { name: 'Begin Prerequisite Probe →' }).click();

      // Screen 3: Probe question check
      await expect(studentBanner).toBeVisible();
      await expect(page.locator('.preview-card')).toContainText('What is 3 - 7?');
      // Click 4 (incorrect)
      await page.getByRole('button', { name: 'B) 4' }).click();
      await expect(page.locator('.preview-feedback-box')).toContainText('evidence supports an integer subtraction gap');
      await page.getByRole('button', { name: 'Proceed to Focused Micro-Lesson' }).click();

      // Screen 4: Micro-lesson check
      await expect(studentBanner).toBeVisible();
      await expect(page.locator('.preview-card')).toContainText('When subtracting a larger positive integer');
      await page.getByRole('button', { name: 'Take Bridge Re-Check →' }).click();

      // Screen 5: Bridge re-check
      await expect(studentBanner).toBeVisible();
      await expect(page.locator('.preview-card')).toContainText('What is 5 - 12?');
      // Click -7 (correct)
      await page.getByRole('button', { name: 'A) -7' }).click();
      await expect(page.locator('.preview-feedback-box')).toContainText('Integer Subtraction: 20% → 45% (illustrative only)');
      await expect(page.locator('.preview-feedback-box')).toContainText('Bridge verified!');

      // Check Restart Preview
      await page.getByRole('button', { name: 'Restart preview' }).first().click();
      await expect(page.locator('.preview-card')).toContainText('Solve for x: x + 7 = 14');

      // Check Back to tour
      await page.getByRole('button', { name: '← Back to tour' }).first().click();
      await expect(page.getByRole('button', { name: 'Open Teacher Dashboard' })).toBeVisible();

      // FIX 3: Test Interactive Teacher Preview
      const openTeacherBtn = page.getByRole('button', { name: 'Open Teacher Dashboard' });
      await openTeacherBtn.click();

      // Teacher persistent banner check
      const teacherBanner = page.locator('.preview-persistent-banner.teacher');
      await expect(teacherBanner).toBeVisible();
      await expect(teacherBanner).toContainText(
        'Prepared preview - synthetic class data, not the live dashboard.'
      );

      // Verify Gap Group & 10-min clinic badge
      await expect(page.locator('.preview-card').first()).toContainText('Addition & Subtraction of Integers');
      await expect(page.locator('.preview-card').first()).toContainText('10-min clinic suggested');

      // Verify Undecided students card
      await expect(page.locator('.preview-card').nth(1)).toContainText('Undecided Students');

      // Test Override functionality
      const overrideBtns = page.locator('button:has-text("Override")');
      await overrideBtns.first().click();

      // Mandatory reason input box
      const reasonTextarea = page.locator('textarea');
      await expect(reasonTextarea).toBeVisible();
      const submitOverrideBtn = page.getByRole('button', { name: 'Submit Override' });
      await expect(submitOverrideBtn).toBeDisabled();

      // Enter reason and submit
      await reasonTextarea.fill('Verified concept mastery during morning clinic session.');
      await expect(submitOverrideBtn).toBeEnabled();
      await submitOverrideBtn.click();

      // Verify confirmation text
      await expect(page.locator('.preview-feedback-box.info')).toContainText(
        'Preview override recorded locally - no real student record changed'
      );

      // Reset teacher preview
      await page.getByRole('button', { name: 'Reset preview' }).first().click();
      await expect(page.locator('.preview-feedback-box.info')).not.toBeVisible();

      // Back to tour options
      await page.getByRole('button', { name: '← Back to tour' }).first().click();
      await expect(page.getByRole('button', { name: 'Open Student App' })).toBeVisible();

      // Finish Tour
      await page.getByRole('button', { name: 'Finish Tour ✓' }).click();
      await expect(page.locator('.tour-overlay')).not.toBeVisible();

      // Verify no console errors
      expect(consoleErrors).toEqual([]);
    });
  }
});
