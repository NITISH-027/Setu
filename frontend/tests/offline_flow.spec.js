import { test, expect } from '@playwright/test';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const screenshotsDir = path.resolve(__dirname, '..', '..', 'screenshots');

test.describe('FIX 3: Offline PWA, Local Engine & IndexedDB Lifecycle', () => {

  test('Comprehensive offline learn-solve-grade flow with real network disconnection and sync', async ({ page, context }) => {
    // Reset stu_e2e_01 attempts and plan so it starts fresh for this test
    const backendDir = path.resolve(__dirname, '..', '..', 'backend');
    execSync(
      `python -c "import sqlite3; con = sqlite3.connect('setu_test.db'); cur = con.cursor(); cur.execute('DELETE FROM attempts WHERE student_id=\\'stu_e2e_01\\''); cur.execute('UPDATE plans SET current_stage=\\'solve\\', stuck_attempts_count=0, bridge_recheck_fails=0 WHERE student_id=\\'stu_e2e_01\\''); con.commit(); con.close()"`,
      { cwd: backendDir }
    );

    page.on('console', msg => console.log('PAGE LOG:', msg.type(), msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

    // Navigate to local preview app
    await page.goto('http://localhost:4173/');
    await expect(page.locator('.brand-title')).toBeVisible();

    // ----------------------------------------------------
    // STEP 1: Sign in online
    // ----------------------------------------------------
    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');

    // Wait until signed in online
    await expect(page.locator('#connection-status-badge')).toHaveText('Online');
    await expect(page.locator('.info-card')).toBeVisible();
    await page.screenshot({ path: path.join(screenshotsDir, '01_online_signin.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 2: Wait until pack and assets are cached in IndexedDB and Service Worker
    // ----------------------------------------------------
    await page.waitForFunction(async () => {
      return new Promise((resolve) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains('packs') || !db.objectStoreNames.contains('profiles')) {
            return resolve(false);
          }
          const tx = db.transaction(['packs', 'profiles'], 'readonly');
          const pReq = tx.objectStore('packs').get('8-A');
          const prReq = tx.objectStore('profiles').get('stu_e2e_01');
          let hasPack = false;
          let hasProfile = false;
          pReq.onsuccess = () => { if (pReq.result) hasPack = true; };
          prReq.onsuccess = () => { if (prReq.result) hasProfile = true; };
          tx.oncomplete = () => resolve(hasPack && hasProfile);
          tx.onerror = () => resolve(false);
        };
        req.onerror = () => resolve(false);
      });
    }, null, { timeout: 15000 });

    // Ensure service worker is controlling page
    await page.waitForFunction(() => {
      return 'serviceWorker' in navigator && navigator.serviceWorker.controller !== null;
    }, null, { timeout: 15000 });

    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(screenshotsDir, '02_cached_pack_and_profile.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 3: Set browser context offline (NOT the UI toggle)
    // ----------------------------------------------------
    await context.setOffline(true);
    await page.screenshot({ path: path.join(screenshotsDir, '03_context_set_offline.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 4: Reload page while offline and confirm app still loads
    // ----------------------------------------------------
    try {
      await page.reload({ timeout: 5000 });
    } catch (e) {
      console.log('Reload error caught:', e.message);
    }
    const html = await page.content();
    console.log('Page content after reload (first 500 chars):', html.slice(0, 500));
    await expect(page.locator('.brand-title')).toBeVisible();
    await expect(page.locator('#student-id-input')).toBeVisible();
    await expect(page.locator('#connection-status-badge')).toHaveText('Offline');
    await page.screenshot({ path: path.join(screenshotsDir, '04_reloaded_offline_loads.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 5: Sign in offline: fail with wrong PIN, then succeed with correct PIN
    // ----------------------------------------------------
    // 5a. Wrong PIN test
    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '0000');
    await page.click('#student-signin-btn');
    await expect(page.locator('#student-status-message')).toContainText('Incorrect PIN');
    await page.screenshot({ path: path.join(screenshotsDir, '05a_wrong_pin_failed.png'), fullPage: true });

    // 5b. Correct PIN test
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');
    await expect(page.locator('.info-card')).toBeVisible();
    await expect(page.locator('#connection-status-badge')).toHaveText('Offline');
    await page.screenshot({ path: path.join(screenshotsDir, '05b_offline_signin_success.png'), fullPage: true });

    // 5c. Verify offline hints appear (Fix 4)
    await expect(page.locator('#request-hint-btn')).toBeVisible();
    await page.click('#request-hint-btn');
    await expect(page.locator('#hint-display-card')).toBeVisible();
    const hintText = await page.locator('#hint-level-1-text').textContent();
    expect(hintText.trim().length).toBeGreaterThan(0);
    await page.screenshot({ path: path.join(screenshotsDir, '05c_offline_hint_displayed.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 6: Answer at least 3 questions offline including one wrong answer
    // ----------------------------------------------------
    // Question 1: Select first option
    const opt1 = page.locator('.option-btn').first();
    await opt1.click();
    await page.click('#submit-attempt-btn');
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screenshotsDir, '06a_offline_q1_answered.png'), fullPage: true });

    // Question 2: Select a different option (intentionally wrong for misconception trigger)
    const opt2 = page.locator('.option-btn').nth(1);
    await opt2.click();
    await page.click('#submit-attempt-btn');
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screenshotsDir, '06b_offline_q2_answered.png'), fullPage: true });

    // Question 3: Select an option
    const opt3 = page.locator('.option-btn').first();
    await opt3.click();
    await page.click('#submit-attempt-btn');
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(screenshotsDir, '06c_offline_q3_answered.png'), fullPage: true });

    // Check queued badge reflects at least 3 attempts
    await expect(page.locator('#queued-count-badge')).toContainText('Queued: 3');

    // ----------------------------------------------------
    // STEP 7: Confirm attempts are in IndexedDB by reading directly in the page
    // ----------------------------------------------------
    const dbAttempts = await page.evaluate(async () => {
      return new Promise((resolve) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('attempts', 'readonly');
          const allReq = tx.objectStore('attempts').getAll();
          allReq.onsuccess = () => resolve(allReq.result);
        };
      });
    });
    expect(dbAttempts.length).toBeGreaterThanOrEqual(3);
    const hasIncorrect = dbAttempts.some((a) => a.is_correct === false);
    expect(hasIncorrect).toBe(true);
    await page.screenshot({ path: path.join(screenshotsDir, '07_indexeddb_attempts_verified.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 8: Reload again while offline and confirm queue is still there
    // ----------------------------------------------------
    await page.reload();
    await expect(page.locator('#student-id-input')).toBeVisible();

    // Sign back in offline
    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');
    await expect(page.locator('.info-card')).toBeVisible();

    // Queue must still be present across page reload!
    await expect(page.locator('#queued-count-badge')).toContainText('Queued: 3');
    await page.screenshot({ path: path.join(screenshotsDir, '08_queue_survives_reload.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 9: Go back online
    // ----------------------------------------------------
    await context.setOffline(false);
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(screenshotsDir, '09_back_online.png'), fullPage: true });

    // ----------------------------------------------------
    // STEP 10: Confirm sync call is made, queue is emptied, and UI shows server mastery
    // ----------------------------------------------------
    const syncBtn = page.locator('#sync-now-btn');
    if (await syncBtn.isEnabled()) {
      await syncBtn.click();
    }

    // Wait until queue is emptied (Queued: 0)
    await expect(page.locator('#queued-count-badge')).toHaveText('Queued: 0', { timeout: 15000 });
    await expect(page.locator('#mastery-estimate-badge')).toBeVisible();
    await expect(page.locator('#sync-now-btn')).toHaveText('Queue Empty');

    // BLOCKER FIX: Verify server has actually saved the synced attempts (not discarded!)
    const out = execSync(
      `python -c "import sqlite3; con = sqlite3.connect('setu_test.db'); cur = con.cursor(); cur.execute('SELECT COUNT(*) FROM attempts WHERE student_id=\\'stu_e2e_01\\''); print(cur.fetchone()[0]); con.close()"`,
      { cwd: backendDir }
    ).toString().trim();
    const serverAttemptCount = parseInt(out, 10);
    expect(serverAttemptCount).toBeGreaterThanOrEqual(3);

    // Verify phone/server state agreement after sync (Fix 2)
    const localLearningState = await page.evaluate(async () => {
      return new Promise((resolve) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('learning_states', 'readonly');
          const getReq = tx.objectStore('learning_states').get('stu_e2e_01');
          getReq.onsuccess = () => {
            const res = getReq.result;
            resolve(res ? (res.state || res) : null);
          };
        };
      });
    });
    expect(localLearningState).toBeTruthy();
    expect(localLearningState.concept_id).toBe('c8_math_linear_eq_one_var');
    expect(localLearningState.stage).toBeDefined();

    await page.screenshot({ path: path.join(screenshotsDir, '10_synced_authoritative_mastery.png'), fullPage: true });
  });

  test('Offline bridge re-check selects questions from gapConcept not primary topic', async ({ page, context }) => {
    // Test Fix 1: Ensure bridge re-check offline selects question from gapConcept
    page.on('console', msg => console.log('T2 LOG:', msg.text()));
    page.on('pageerror', err => console.log('T2 ERROR:', err.message));
    const backendDir = path.resolve(__dirname, '..', '..', 'backend');

    // 1. Visit app and sign in online to cache pack
    await page.goto('http://localhost:4173/');
    await page.fill('#student-id-input', 'stu_e2e_02');
    await page.fill('#student-pin-input', '9876');
    await page.click('#student-signin-btn');
    await expect(page.locator('.info-card')).toBeVisible({ timeout: 10000 });

    // Wait until pack and profile are stored in IndexedDB
    await page.waitForFunction(async () => {
      return new Promise((resolve) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains('packs') || !db.objectStoreNames.contains('profiles')) return resolve(false);
          const tx = db.transaction(['packs', 'profiles'], 'readonly');
          const pReq = tx.objectStore('packs').get('8-A');
          const prReq = tx.objectStore('profiles').get('stu_e2e_02');
          let hasPack = false;
          let hasProfile = false;
          pReq.onsuccess = () => { if (pReq.result) hasPack = true; };
          prReq.onsuccess = () => { if (prReq.result) hasProfile = true; };
          tx.oncomplete = () => resolve(hasPack && hasProfile);
          tx.onerror = () => resolve(false);
        };
        req.onerror = () => resolve(false);
      });
    }, null, { timeout: 15000 });

    // Seed offline learning_states directly into IndexedDB for bridge_recheck with gapConcept
    await page.evaluate(async () => {
      return new Promise((resolve) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => {
          const db = req.result;
          const tx = db.transaction('learning_states', 'readwrite');
          tx.objectStore('learning_states').put({
            student_id: 'stu_e2e_02',
            state: {
              stage: 'bridge_recheck',
              concept_id: 'c8_math_linear_eq_one_var',
              gap_concept_id: 'c6_math_integers_add_sub',
              mastery: 0.35,
              stuck_attempts: 0,
              bridge_recheck_fails: 0
            },
            updated_at: new Date().toISOString()
          });
          tx.oncomplete = () => resolve(true);
        };
      });
    });

    // 2. Go offline
    await context.setOffline(true);
    await page.reload();

    // 3. Sign in offline
    await page.fill('#student-id-input', 'stu_e2e_02');
    await page.fill('#student-pin-input', '9876');
    await page.click('#student-signin-btn');

    // 4. Verify stage is bridge_recheck
    await expect(page.locator('.badge-stage')).toHaveText('bridge_recheck', { timeout: 10000 });

    // 5. Verify the question presented belongs to the prerequisite gapConcept ('c6_math_integers_add_sub'), NOT 'c8_math_linear_eq_one_var'
    await expect(page.locator('#question-card')).toBeVisible();
    const activeConcept = await page.locator('#question-card').getAttribute('data-concept');
    expect(activeConcept).toBe('c6_math_integers_add_sub');
  });

});
