// Playwright scenarios from SCENARIOS.md ("In a browser"): one test per scenario, named after its title.
// Serves tests/e2e/pages and browser/ from 127.0.0.1, blocks every other host, and opens headless Chromium.
//   npm ci --prefix tests/e2e --ignore-scripts && tests/e2e/node_modules/.bin/playwright install chromium
//   node --test tests/e2e/furigana.e2e.mjs
// (or put an existing playwright on NODE_PATH, and a Chromium in CHROME).
import test, {after, before} from 'node:test';
import assert from 'node:assert/strict';
import {createReadStream, existsSync, statSync} from 'node:fs';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const require = createRequire(import.meta.url);
const {chromium} = (() => {try {return require('playwright');} catch {return require('playwright-core');}})();
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const SERVED = {'/pages/': path.join(root, 'tests/e2e/pages'), '/browser/': path.join(root, 'browser')};
const TYPES = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8'};
// Headless Chromium on macOS asks for a keychain without these (test-core lesson); harmless elsewhere.
const CHROMIUM_ARGS = ['--use-mock-keychain', '--password-store=basic'];

let server, browser, base;
const external = [];

before(async () => {
  server = createServer((request, response) => {
    const url = new URL(request.url, 'http://127.0.0.1');
    const prefix = Object.keys(SERVED).find(p => url.pathname.startsWith(p));
    const file = prefix && path.join(SERVED[prefix], path.normalize(url.pathname.slice(prefix.length)));
    if (!file || !file.startsWith(SERVED[prefix]) || !existsSync(file) || !statSync(file).isFile()) {
      response.writeHead(404).end('not found');
      return;
    }
    response.writeHead(200, {'content-type': TYPES[path.extname(file)] || 'application/octet-stream'});
    createReadStream(file).pipe(response);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({headless: true, args: CHROMIUM_ARGS,
    ...(process.env.CHROME ? {executablePath: process.env.CHROME} : {})});
});

after(async () => {
  await browser?.close();
  await new Promise(resolve => server ? server.close(resolve) : resolve());
  assert.deepEqual(external, [], 'the pages must not reach any other host');
});

async function newPage() {
  const context = await browser.newContext();
  await context.route('**/*', route => {
    if (new URL(route.request().url()).hostname === '127.0.0.1') return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  return {context, page, errors};
}

test('Hide and show furigana with the toggle button', async () => {
  const {context, page, errors} = await newPage();
  try {
    // Given the page jp_core.web builds with ruby text and the furigana toggle
    await page.goto(`${base}/pages/furigana.html`);
    const toggle = page.getByRole('button', {name: 'ふりがな'});
    const reading = page.locator('#sentence rt').first();
    await assert.doesNotReject(reading.waitFor({state: 'visible'}));
    assert.equal(await toggle.getAttribute('aria-pressed'), 'true');
    // When I press the toggle
    await toggle.click();
    // Then the readings hide
    await reading.waitFor({state: 'hidden'});
    assert.equal(await page.locator('#sentence').innerText(), '日本語を勉強します。');
    // and the choice survives the reload, with the button saying not pressed
    await page.reload();
    await page.locator('#sentence rt').first().waitFor({state: 'hidden'});
    assert.equal(await page.getByRole('button', {name: 'ふりがな'}).getAttribute('aria-pressed'), 'false');
    // When I press it again, they come back
    await page.getByRole('button', {name: 'ふりがな'}).click();
    await page.locator('#sentence rt').first().waitFor({state: 'visible'});
    assert.deepEqual(errors, []);
  } finally {
    await context.close();
  }
});

test('The browser module renders ruby in Chromium', async () => {
  const {context, page, errors} = await newPage();
  try {
    await page.goto(`${base}/pages/module.html`);
    await page.waitForFunction(() => document.body.dataset.ready === 'true');
    assert.equal(await page.locator('#out ruby').count(), 1);
    assert.equal(await page.locator('#out rt').innerText(), 'にほんご');
    assert.equal(await page.locator('#out img').count(), 0);
    assert.equal(await page.evaluate(() => window.injected), undefined);
    assert.match(await page.locator('#out').innerText(), /^<img src=x onerror="window.injected=1">/);
    assert.deepEqual(errors, []);
  } finally {
    await context.close();
  }
});
