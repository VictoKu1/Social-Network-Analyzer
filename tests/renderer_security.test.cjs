/* Run with: node --test tests/renderer_security.test.cjs
 * Requires Playwright and an installed Chrome (or CHROME_EXECUTABLE_PATH).
 * The browser only receives local files and synthetic API responses; no app,
 * social network, model endpoint, credentials, or external network is used.
 */
const assert = require('node:assert/strict');
const { before, after, test } = require('node:test');
const { readFile } = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');

const root = path.resolve(__dirname, '..');
let browser;

before(async () => {
  browser = await chromium.launch({
    executablePath: process.env.CHROME_EXECUTABLE_PATH ||
      'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: true,
  });
});
after(async () => { await browser?.close(); });

async function renderAnalysis(markdown, inspect, csp) {
  const page = await browser.newPage();
  const mediaRequests = [];
  try {
    await page.addInitScript(() => { window.__rendererExecuted = false; });
    await page.route('**/*', async (route) => {
      const request = route.request();
      const url = new URL(request.url());
      if (['image', 'media'].includes(request.resourceType())) mediaRequests.push(url.href);
      if (url.pathname === '/api/llm-config') {
        return route.fulfill({ json: {
          default_provider: 'openai', openai: { configured: true, model: 'synthetic-test-model' },
          ollama: { configured_model: '' },
        } });
      }
      if (url.pathname === '/validate_links') {
        return route.fulfill({ json: {
          all_valid: true,
          results: [{ url: 'https://github.com/example', platform: 'GitHub', is_valid: true }],
        } });
      }
      if (url.pathname === '/analyze') return route.fulfill({ json: { analysis: markdown } });
      if (url.pathname === '/') {
        return route.fulfill({
          contentType: 'text/html',
          headers: csp ? { 'Content-Security-Policy': csp } : {},
          body: await readFile(path.join(root, 'templates/index.html'), 'utf8'),
        });
      }
      // Exercise the existing CDN-based renderer when reproducing the bug, but
      // provide the parser from disk so even the pre-fix test stays offline.
      if (url.hostname === 'cdn.jsdelivr.net') {
        const markedRoot = path.dirname(require.resolve('marked/package.json'));
        return route.fulfill({ contentType: 'application/javascript', body: await readFile(path.join(markedRoot, 'lib/marked.umd.js'), 'utf8') });
      }
      if (url.hostname === '127.0.0.1' && url.pathname.startsWith('/static/')) {
        const file = path.resolve(root, '.' + url.pathname);
        if (file.startsWith(root + path.sep)) {
          const contentType = file.endsWith('.js') ? 'application/javascript' : 'text/css';
          return route.fulfill({ contentType, body: await readFile(file, 'utf8') });
        }
      }
      return route.fulfill({ status: 404, body: '' });
    });
    await page.goto('http://127.0.0.1:8765/');
    await page.selectOption('#numLinks', '1');
    await page.click('#setupContinue');
    await page.fill('#link_0', 'https://github.com/example');
    await page.click('#continueBtn');
    await page.fill('#personalDescription', 'A synthetic renderer regression fixture.');
    await page.click('#analyzeBtn');
    await page.locator('#analysisResult').waitFor({ state: 'visible' });
    await inspect(page, mediaRequests);
  } finally {
    await page.close();
  }
}

test('model HTML cannot create executable elements, handlers, or clobber application IDs', async () => {
  await renderAnalysis([
    '<img src="/missing-image" onerror="window.__rendererExecuted=true">',
    '<svg onload="window.__rendererExecuted=true"><a href="javascript:window.__rendererExecuted=true">x</a></svg>',
    '<iframe srcdoc="<script>parent.__rendererExecuted=true</script>"></iframe>',
    '<form id="stepA"><input name="analysisText"></form>',
    '<p style="position:fixed" onclick="window.__rendererExecuted=true">Injected</p>',
  ].join('\n'), async (page) => {
    assert.equal(await page.evaluate(() => window.__rendererExecuted), false);
    assert.equal(await page.locator('#analysisText img, #analysisText svg, #analysisText iframe, #analysisText form, #analysisText input').count(), 0);
    assert.deepEqual(await page.locator('#analysisText *').evaluateAll((elements) => elements.flatMap((element) =>
      [...element.attributes].filter((attribute) => /^(on|style$|id$|name$)/i.test(attribute.name)).map((attribute) => attribute.name))), []);
    assert.equal(await page.locator('#stepA').count(), 1);
  });
});

test('Markdown and HTML images cannot fetch remote or local media', async () => {
  await renderAnalysis('![Profile picture](https://renderer-test.invalid/pixel)\n\n<img src="/private-image">', async (page, mediaRequests) => {
    assert.equal(await page.locator('#analysisText img, #analysisText video, #analysisText audio, #analysisText source').count(), 0);
    assert.deepEqual(mediaRequests, []);
    assert.match(await page.locator('#analysisText').textContent(), /Profile picture/);
  });
});

test('unsafe Markdown URLs remain inert and safe HTTPS links retain their labels', async () => {
  await renderAnalysis([
    '[script](javascript:alert%281%29)',
    '[data](data:text/html,test)',
    '[local](/api/ollama/models)',
    '[relative](//example.com/profile)',
    '[encoded](javascript&#58;alert%281%29)',
    '[credentials](https://user:password@example.com/)',
    '[safe](https://example.com/profile)',
  ].join('\n\n'), async (page) => {
    const links = await page.locator('#analysisText a').evaluateAll((elements) => elements.map((element) => ({ href: element.getAttribute('href'), label: element.textContent, rel: element.rel })));
    assert.deepEqual(links, [{ href: 'https://example.com/profile', label: 'safe', rel: 'noopener noreferrer' }]);
    assert.match(await page.locator('#analysisText').textContent(), /script/);
  });
});

test('Markdown formatting still works with scripts restricted to this application', async () => {
  await renderAnalysis('| Trait | Score |\n| --- | --- |\n| Curiosity | **82** |', async (page) => {
    assert.deepEqual(await page.locator('#analysisText td').allTextContents(), ['Curiosity', '82']);
    assert.equal(await page.locator('#analysisText td strong').textContent(), '82');
  }, "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
});

test('normal Markdown preserves headings, emphasis, lists, code, and score tables', async () => {
  await renderAnalysis('# Summary\n\nA **thoughtful** and *curious* profile.\n\n- First item\n- Second item\n\n| Trait | Score |\n| --- | --- |\n| Curiosity | 82 |\n\n```html\n<img onerror="alert(1)">\n```', async (page) => {
    assert.equal(await page.locator('#analysisText h1').textContent(), 'Summary');
    assert.equal(await page.locator('#analysisText strong').textContent(), 'thoughtful');
    assert.equal(await page.locator('#analysisText em').textContent(), 'curious');
    assert.deepEqual(await page.locator('#analysisText li').allTextContents(), ['First item', 'Second item']);
    assert.deepEqual(await page.locator('#analysisText th').allTextContents(), ['Trait', 'Score']);
    assert.deepEqual(await page.locator('#analysisText td').allTextContents(), ['Curiosity', '82']);
    assert.match(await page.locator('#analysisText pre code').textContent(), /<img onerror="alert\(1\)">/);
    assert.equal(await page.locator('#analysisText img').count(), 0);
  });
});
