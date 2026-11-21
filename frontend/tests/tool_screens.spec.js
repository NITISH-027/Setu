import { test, expect } from '@playwright/test';

for (const width of [320,390,1440]) test(`Lilac tour keeps all five steps and honest prepared previews at ${width}px`, async ({ page }) => {
  await page.setViewportSize({width,height:900});
  await page.goto('http://localhost:4173');
  await page.locator('#guided-tour-btn').click();
  for (let step = 1; step <= 5; step++) {
    await expect(page.locator('.tour-step-counter')).toContainText(`Step ${step} of 5`);
    const bounds = await page.locator('.tour-modal-content').boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    expect(await page.locator('.tour-body').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    if (step < 5) await page.getByRole('button', {name:'Next →',exact:true}).click();
  }
  const writes=[]; page.on('request',r=>{if(r.method()==='POST')writes.push(r.url());});
  await page.getByRole('button',{name:'Open Student App',exact:true}).click();
  await expect(page.locator('.preview-persistent-banner')).toContainText('Not connected to the live engine');
  await page.getByRole('button',{name:'B) 21',exact:true}).click();
  await expect(page.locator('.preview-feedback-box')).toContainText('Incorrect');
  await page.getByRole('button',{name:'← Back to tour',exact:true}).click();
  await page.getByRole('button',{name:'Open Teacher Dashboard',exact:true}).click();
  await expect(page.locator('.preview-persistent-banner')).toContainText('synthetic class data');
  await page.getByRole('button',{name:'Override',exact:true}).first().click();
  await page.locator('.tour-body textarea').fill('Prepared preview: reviewed the supporting evidence.');
  await page.getByRole('button',{name:'Submit Override',exact:true}).click();
  await expect(page.locator('.preview-feedback-box.info')).toContainText('no real student record changed');
  expect(writes).toEqual([]);
  await page.getByRole('button',{name:'Close Tour',exact:true}).click();
  await expect(page.locator('.tour-overlay')).toHaveCount(0);
});

test('Paper mode keeps teacher auth, printable HTML, row controls and real server bulk grading', async ({page}) => {
  await page.goto('http://localhost:4173');
  await page.locator('#tab-paper').click();
  await expect(page.locator('.paper-example-note')).toContainText('Example rows');
  for (const width of [320,390,768,1440]) {
    await page.setViewportSize({width,height:900});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await page.locator('#teacher-paper-username').fill('tea_e2e_8a');
  await page.locator('#teacher-paper-password').fill('tea_e2e_pass');
  await page.getByRole('button',{name:'Sign In',exact:true}).click();
  await expect(page.locator('.paper-ready')).toBeVisible();
  const popup = page.waitForEvent('popup');
  const sheet = page.waitForResponse(r=>r.url().includes('/api/paper/sheet/'));
  await page.getByRole('button',{name:'Open Printable Sheet in New Tab',exact:true}).click();
  expect((await sheet).status()).toBe(200);
  const printed = await popup;
  await expect(printed.locator('h2')).toContainText('Setu Paper Mode Worksheet');
  await expect(printed.locator('.q-box').first()).toContainText('q_c8_leq_01');
  await printed.close();
  await page.getByRole('button',{name:'+ Add Student Row',exact:true}).click();
  await expect(page.locator('.paper-entry-row')).toHaveCount(3);
  await page.getByRole('button',{name:'Remove row 3',exact:true}).click();
  await page.getByRole('button',{name:'Remove row 2',exact:true}).click();
  await page.locator('#bulk-student-id-0').fill('stu_e2e_01');
  await page.locator('#bulk-question-id-0').fill('q_c8_leq_01');
  await page.locator('#bulk-option-id-0').fill('opt_1');
  await page.locator('#process-bulk-paper-btn').click();
  await expect(page.locator('#bulk-paper-success')).toContainText('Processed 1');
  await expect(page.locator('#bulk-paper-success')).toContainText('stu_e2e_01');
  await page.locator('#bulk-option-id-0').fill('invalid_option');
  await page.locator('#process-bulk-paper-btn').click();
  await expect(page.locator('#bulk-paper-errors')).toBeVisible();
  await expect(page.locator('#bulk-paper-errors')).toContainText('stu_e2e_01');
});

test('Shared header preserves language, saved theme and tools navigation', async ({page}) => {
  await page.goto('http://localhost:4173');
  await page.locator('#tab-paper').click();
  await page.locator('.learning-display summary').click();
  await page.locator('#language-select').selectOption('hi');
  await expect(page.locator('#tab-paper')).toHaveText('▤पेपर मोड');
  await page.locator('#language-select').selectOption('en');
  await page.locator('#theme-select').selectOption('amethyst');
  await expect(page.locator('html')).toHaveAttribute('data-theme','amethyst');
  await page.reload();
  await page.locator('#tab-paper').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme','amethyst');
  await page.locator('#tab-privacy').click();
  await expect(page.locator('#tab-privacy')).toHaveAttribute('aria-current','page');
});
