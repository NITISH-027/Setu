import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const screenshotsDir = path.resolve(__dirname, '..', '..', 'screenshots');

test.describe('FIX 4: Stale Device Reset & Client IndexedDB Wipe', () => {
  test('Browser receives RESET-required response on sync and completely wipes IndexedDB student data', async ({ page }) => {
    page.on('console', msg => console.log('RESET PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('RESET PAGE ERROR:', err.message));

    // 1. Visit app and sign in online as student
    await page.goto('http://localhost:4173/');
    await expect(page.locator('.brand-title')).toBeVisible();

    await page.fill('#student-id-input', 'stu_e2e_01');
    await page.fill('#student-pin-input', '5678');
    await page.click('#student-signin-btn');

    // Confirm student dashboard loaded
    await expect(page.locator('#connection-status-badge')).toHaveText('Online');
    await expect(page.locator('.info-card')).toBeVisible();

    // Wait until profile and pack are cached
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
    }, null, { timeout: 10000 });

    // 2. Disconnect and answer a question offline to populate IndexedDB
    await page.context().setOffline(true);
    await expect(page.locator('#connection-status-badge')).toHaveText('Offline');

    const opt = page.locator('.option-btn').first();
    await opt.click();
    await page.click('#submit-attempt-btn');
    await page.waitForTimeout(600);

    // Confirm queue has 1 item
    await expect(page.locator('#queued-count-badge')).toContainText('Queued: 1', { timeout: 10000 });

    // Verify IndexedDB has attempts and sync queue items before wipe
    const beforeWipe = await page.evaluate(async () => {
      const openDB = () => new Promise((resolve, reject) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
      const db = await openDB();
      const count = (storeName) => new Promise((res) => {
        const tx = db.transaction(storeName, 'readonly');
        const req = tx.objectStore(storeName).count();
        req.onsuccess = () => res(req.result);
      });
      return {
        attempts: await count('attempts'),
        sync_queue: await count('sync_queue'),
        profiles: await count('profiles')
      };
    });

    expect(beforeWipe.attempts).toBeGreaterThan(0);
    expect(beforeWipe.sync_queue).toBeGreaterThan(0);
    expect(beforeWipe.profiles).toBeGreaterThan(0);

    // 3. Intercept sync route to return RESET response (stale or unregistered device policy) BEFORE reconnecting
    await page.route('**/api/privacy/sync', async (route) => {
      console.log('RESET TEST: Intercepted /api/privacy/sync request!');
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_stale_reset_required: true,
          reason: 'Device stale: 30+ days without sync or unregistered device policy'
        })
      });
    });

    console.log('RESET TEST: Setting offline false...');
    await page.context().setOffline(false);
    await expect(page.locator('#connection-status-badge')).toHaveText('Online');
    console.log('RESET TEST: Reconnected online!');

    // 4. Trigger sync (either automatic on reconnect or click button if visible)
    const syncBtn = page.locator('#sync-now-btn');
    if (await syncBtn.isVisible()) {
      console.log('RESET TEST: Sync button is visible, waiting for enabled and clicking...');
      await syncBtn.click({ timeout: 5000 }).catch(err => console.log('RESET TEST: Sync button click caught:', err.message));
    }

    // 5. Verify UI logs out student and displays reset message
    console.log('RESET TEST: Waiting for reset message...');
    const statusMsg = page.locator('#student-status-message');
    await expect(statusMsg).toBeVisible({ timeout: 15000 });
    await expect(statusMsg).toContainText('Device cache reset required');
    await expect(page.locator('#student-pin-input')).toBeVisible();
    console.log('RESET TEST: Student logged out and reset message verified!');

    // 6. Verify IndexedDB is completely wiped
    const afterWipe = await page.evaluate(async () => {
      const openDB = () => new Promise((resolve, reject) => {
        const req = indexedDB.open('SetuOfflineDB', 1);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
      const db = await openDB();
      const count = (storeName) => new Promise((res) => {
        const tx = db.transaction(storeName, 'readonly');
        const req = tx.objectStore(storeName).count();
        req.onsuccess = () => res(req.result);
      });
      return {
        attempts: await count('attempts'),
        sync_queue: await count('sync_queue'),
        profiles: await count('profiles'),
        learning_states: await count('learning_states')
      };
    });

    expect(afterWipe.attempts).toBe(0);
    expect(afterWipe.sync_queue).toBe(0);
    expect(afterWipe.profiles).toBe(0);
    expect(afterWipe.learning_states).toBe(0);

    await page.screenshot({ path: path.join(screenshotsDir, '11_device_reset_wiped_indexeddb.png'), fullPage: true });
  });
});
