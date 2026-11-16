import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from 'playwright';

const root = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(root, 'browser-evidence');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
const errors = [];
const external = [];
page.on('pageerror', error => errors.push(String(error)));
page.on('request', request => {
  if (/^https?:/i.test(request.url())) external.push(request.url());
});
try {
  await page.goto(pathToFileURL(path.join(root, 'demo', 'index.html')).href);
  await page.waitForSelector('svg#plot polyline');
  assert.equal(await page.locator('#nAssigned').innerText(), '1191');
  assert.equal(await page.locator('#nPredicted').innerText(), '1192');
  assert.equal(await page.locator('#nFP').innerText(), '1');
  assert.equal(await page.locator('[data-case="freeze"]').getAttribute('aria-pressed'), 'true');
  await page.screenshot({ path: path.join(out, 'screenshot_desktop.png'), fullPage: true });

  await page.locator('[data-case="clean"]').click();
  assert.equal(await page.locator('#nAssigned').innerText(), '0');
  assert.equal(await page.locator('#nPredicted').innerText(), '0');
  await page.locator('[data-case="standing"]').click();
  assert.equal(await page.locator('#nAssigned').innerText(), '0');
  assert.equal(await page.locator('#nFP').innerText(), '0');
  await page.locator('[data-case="freeze"]').click();
  await page.locator('[data-axis="y"]').click();
  assert.equal(await page.locator('[data-axis="y"]').getAttribute('aria-pressed'), 'true');
  await page.locator('[data-axis="x"]').click();
  await page.locator('[data-zoom="boundary"]').click();
  assert.equal(await page.locator('[data-zoom="boundary"]').getAttribute('aria-pressed'), 'true');
  await page.locator('[data-visible="reference"]').uncheck();
  assert.equal(await page.locator('[data-visible="reference"]').isChecked(), false);
  await page.locator('[data-visible="reference"]').check();
  await page.locator('#reset').click();
  await page.locator('#plot').screenshot({ path: path.join(out, 'screenshot_boundary.png') });
  assert.deepEqual(errors, [], 'Browser JavaScript must not throw');
  assert.deepEqual(external, [], 'Static HTML must not fetch network resources');
  console.log('PASS: browser scenarios, controls, masks, no JS exceptions or HTTP(S) requests');
} finally {
  await browser.close();
}
