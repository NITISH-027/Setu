import { test, expect } from '@playwright/test';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const screenshotsDir = path.resolve(__dirname, '..', '..', 'screenshots');

test.describe('FIX 1: Offline Deletion Propagation to Device', () => {
  test('Deleted student purged on device reconnect via purge-only credential; offline sign-in fails; other device unaffected', async ({ page }) => {
    // Reset stu_e2e_01 attempts and plan so it starts fresh for this test
    const backendDir = path.resolve(__dirname, '..', '..', 'backend');
    execSync(
      `python -c "import sqlite3; con = sqlite3.connect('setu_test.db'); cur = con.cursor(); cur.execute('DELETE FROM attempts WHERE student_id=\\'stu_e2e_01\\''); cur.execute('UPDATE plans SET current_stage=\\'solve\\', stuck_attempts_count=0, bridge_recheck_fails=0 WHERE student_id=\\'stu_e2e_01\\''); con.commit(); con.close()"`,
      { cwd: backendDir }
    );

    // 1. Sign in student A (stu_e2e_01) on Device 1 in real browser
    await page.goto('http://localhost:4173/');
    await expect(page.locator('.brand-title')).toBeVisible();

    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');

    // Confirm student dashboard loaded online
    await expect(page.locator('#connection-status-badge')).toHaveText('Online');
    await expect(page.locator('.info-card')).toBeVisible();

    // Verify profile, PBKDF2 verifier, and subject_key are cached in IndexedDB
    await page.waitForFunction(async () => {
      return new Promise((resolve) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains('profiles') || !db.objectStoreNames.contains('metadata')) {
            return resolve(false);
          }
          const tx = db.transaction(['profiles', 'metadata'], 'readonly');
          const pReq = tx.objectStore('profiles').get('stu_e2e_01');
          const mReq = tx.objectStore('metadata').get('device_purge_token');
          let hasProf = false;
          let hasToken = false;
          pReq.onsuccess = () => { if (pReq.result && pReq.result.pin_verifier) hasProf = true; };
          mReq.onsuccess = () => { if (mReq.result && mReq.result.value) hasToken = true; };
          tx.oncomplete = () => resolve(hasProf && hasToken);
          tx.onerror = () => resolve(false);
        };
        req.onerror = () => resolve(false);
      });
    }, null, { timeout: 10000 });

    // 2. Go offline
    await page.context().setOffline(true);
    await expect(page.locator('#connection-status-badge')).toHaveText('Offline');

    // Answer a question offline to populate attempts and queue
    const opt = page.locator('.option-btn').first();
    await opt.click();
    await page.click('#submit-attempt-btn');
    await page.waitForTimeout(600);
    await expect(page.locator('#queued-count-badge')).toContainText('Queued: 1', { timeout: 10000 });

    // 3. Teacher deletes student A through real backend route while device is offline
    // Teacher signs in via real API
    const teacherLoginRes = await fetch('http://127.0.0.1:8000/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'tea_e2e_8a', password: 'tea_e2e_pass' })
    });
    expect(teacherLoginRes.ok).toBeTruthy();
    const teacherAuth = await teacherLoginRes.json();
    const teacherToken = teacherAuth.access_token;

    // Call real delete route
    const deleteRes = await fetch('http://127.0.0.1:8000/api/privacy/delete-student', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${teacherToken}`
      },
      body: JSON.stringify({ student_id: 'stu_e2e_01' })
    });
    expect(deleteRes.ok).toBeTruthy();
    const deleteJson = await deleteRes.json();
    const tombstoneKey = deleteJson.tombstone_key;

    // Assert that ONLY Device 1 (which held student A) is pending!
    // Device 2 (dev_tablet_02, which only held student B) does NOT count as pending!
    expect(deleteJson.pending_devices).toBe(1);
    expect(deleteJson.is_fully_deleted_everywhere).toBe(false);

    // 4. Device 1 comes back online
    await page.context().setOffline(false);
    await expect(page.locator('#connection-status-badge')).toHaveText('Online');

    // Trigger sync / purge check if button still visible (reconnect auto-sync may have unmounted it already)
    const syncBtn = page.locator('#sync-now-btn');
    if (await syncBtn.isVisible()) {
      await syncBtn.click({ timeout: 2000 }).catch(() => {});
    }
    await page.waitForTimeout(1500);

    // 5. Assert IndexedDB for Student A is completely empty!
    const studentDataAfterPurge = await page.evaluate(async () => {
      const openDB = () => new Promise((resolve, reject) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
      const db = await openDB();
      const getProfile = () => new Promise((res) => {
        const tx = db.transaction('profiles', 'readonly');
        const req = tx.objectStore('profiles').get('stu_e2e_01');
        req.onsuccess = () => res(req.result || null);
        req.onerror = () => res(null);
      });
      const getState = () => new Promise((res) => {
        const tx = db.transaction('learning_states', 'readonly');
        const req = tx.objectStore('learning_states').get('stu_e2e_01');
        req.onsuccess = () => res(req.result || null);
        req.onerror = () => res(null);
      });
      return {
        profile: await getProfile(),
        state: await getState()
      };
    });

    expect(studentDataAfterPurge.profile).toBeNull();
    expect(studentDataAfterPurge.state).toBeNull();

    // 6. Assert offline sign-in as Student A now fails!
    // Go offline again
    await page.context().setOffline(true);
    await expect(page.locator('#connection-status-badge')).toHaveText('Offline');

    // Fill sign-in form with Student A credentials
    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');

    // Must fail because offline profile verifier was wiped!
    await expect(page.locator('#student-status-message')).toContainText('No offline profile found on this device', { timeout: 10000 });

    // 7. Assert tombstone shows acknowledged for Device 1 via teacher privacy metrics
    const metricsRes = await fetch('http://127.0.0.1:8000/api/teacher/privacy-metrics', {
      headers: { 'Authorization': `Bearer ${teacherToken}` }
    });
    expect(metricsRes.ok).toBeTruthy();
    const metrics = await metricsRes.json();
    const tomb = metrics.tombstones.find((t) => t.opaque_key === tombstoneKey);
    expect(tomb).toBeDefined();
    expect(tomb.status).toBe('applied');
    expect(tomb.pending_devices).toBe(0);

    const deliveryDev1 = metrics.deliveries.find((d) => d.opaque_key === tombstoneKey && d.device_id === 'dev_demo_tablet');
    expect(deliveryDev1).toBeDefined();
    expect(deliveryDev1.status).toBe('acknowledged');

    // 8. Assert a second, different device (dev_tablet_02) that never held A is NOT affected and does NOT count as pending
    const deliveryDev2 = metrics.deliveries.find((d) => d.opaque_key === tombstoneKey && d.device_id === 'dev_tablet_02');
    expect(deliveryDev2).toBeUndefined(); // Device 2 never had a delivery for this student!

    await page.screenshot({ path: path.join(screenshotsDir, '12_offline_deletion_device_acknowledged.png'), fullPage: true });
  });

  test.afterAll(async () => {
    try {
      const backendDir = path.resolve(__dirname, '..', '..', 'backend');
      const seedScript = path.resolve(__dirname, '..', '..', 'scripts', 'seed_e2e_fixtures.py');
      const { execSync } = await import('child_process');
      execSync(`python "${seedScript}"`, {
        env: { ...process.env, SETU_TEST_ENV: '1', DATABASE_URL: 'sqlite:///./setu_test.db' },
        cwd: backendDir,
        stdio: 'ignore'
      });
    } catch {
      // Ignore
    }
  });
});
