// Run after npm run build, with the local API and Vite preview running.
// node scripts/benchmark_3g.mjs http://127.0.0.1:4173
import { chromium } from '@playwright/test';
const base = process.argv[2] || 'http://127.0.0.1:4173';
if (!['localhost', '127.0.0.1', '[::1]'].includes(new URL(base).hostname)) {
  throw new Error('Local targets only. Do not benchmark the deployed demo.');
}
const browser = await chromium.launch({ headless: true });
const runs = [];
try {
  for (let i = 0; i < 3; i++) {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
    const page = await context.newPage();
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false, latency: 100, downloadThroughput: 750000 / 8, uploadThroughput: 250000 / 8,
      connectionType: 'cellular3g'
    });
    const failed = [];
    page.on('requestfailed', req => failed.push(new URL(req.url()).pathname));
    page.on('response', res => { if (res.status() >= 400) failed.push(`${res.status()} ${new URL(res.url()).pathname}`); });
    const start = Date.now();
    await page.goto(base, { waitUntil: 'load' });
    await page.locator('#tab-teacher').waitFor({ state: 'visible' });
    const appReadyMs = Date.now() - start;
    await page.waitForLoadState('networkidle');
    const metrics = await page.evaluate(() => {
      const nav = performance.getEntriesByType('navigation')[0];
      const resources = performance.getEntriesByType('resource');
      const all = [nav, ...resources];
      return {
        loadEventMs: Math.round(nav.loadEventEnd),
        firstContentfulPaintMs: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0),
        transferBytes: all.reduce((sum, r) => sum + r.transferSize, 0),
        encodedBodyBytes: all.reduce((sum, r) => sum + r.encodedBodySize, 0),
        decodedBodyBytes: all.reduce((sum, r) => sum + r.decodedBodySize, 0),
        resourceCount: all.length,
      };
    });
    runs.push({ run: i + 1, appReadyMs, ...metrics, failed });
    if (failed.length) throw new Error('A local request failed: ' + JSON.stringify(failed));
    await context.close();
  }
  console.log(JSON.stringify({ scope: 'Local production build landing screen, mobile viewport, cold HTTP cache, service worker blocked',
    network: { latencyMs: 100, downloadKbps: 750, uploadKbps: 250, cpuThrottling: false },
    browser: browser.version(), generatedAtUtc: new Date().toISOString(), runs,
    limitations: 'Synthetic 3G profile, not a real mobile network. Local server; no Render cold start, internet path, or Neon latency. PWA installation/background precache excluded. App-ready means navigation tabs visible, not a downloaded lesson or completed diagnosis.' }, null, 2));
} finally {
  await browser.close();
}
