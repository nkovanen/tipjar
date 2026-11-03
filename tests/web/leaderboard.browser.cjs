/* Optional real Chromium QA: TIPJAR_PLAYWRIGHT=/absolute/path/to/playwright node tests/web/leaderboard.browser.cjs */
'use strict';
const { chromium } = require(process.env.TIPJAR_PLAYWRIGHT || 'playwright');
const assert = require('node:assert/strict'),
  fs = require('node:fs'),
  http = require('node:http'),
  path = require('node:path');
const root = path.resolve(__dirname, '../..'),
  output = process.env.TIPJAR_BROWSER_EVIDENCE || '/tmp/tipjar-board-browser';
const fixture = (name) =>
  JSON.parse(fs.readFileSync(path.join(root, `tests/fixtures/tipjar-board/${name}.json`), 'utf8'));
(async () => {
  fs.mkdirSync(output, { recursive: true });
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    const file = path.resolve(
      root,
      '.' + url.pathname.replace(/^\/tipjar/, '/web').replace(/\/$/, '/index.html'),
    );
    if (!file.startsWith(root + path.sep)) {
      res.writeHead(403).end();
      return;
    }
    fs.readFile(file, (err, data) => {
      if (err) {
        res.writeHead(404).end();
        return;
      }
      res.setHeader(
        'Content-Type',
        file.endsWith('.js')
          ? 'text/javascript'
          : file.endsWith('.css')
            ? 'text/css'
            : file.endsWith('.svg')
              ? 'image/svg+xml'
              : file.endsWith('.json')
                ? 'application/json'
                : 'text/html',
      );
      res.end(data);
    });
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`,
    browser = await chromium.launch({ headless: true });
  let checks = 0;
  async function page(width = 1280, data = fixture('valid')) {
    const p = await browser.newPage({
      viewport: { width, height: 1000 },
      reducedMotion: 'reduce',
    });
    await p.clock.install({ time: new Date('2026-11-03T13:00:00Z') });
    const errors = [];
    p.on('pageerror', (e) => errors.push(e.message));
    p.errors = errors;
    await p.route('**/tipjar/board.json', (route) =>
      route.fulfill({
        status: data === null ? 404 : 200,
        contentType: 'application/json',
        body: data === null ? '' : JSON.stringify(data),
      }),
    );
    return p;
  }
  async function suggestionLink(p, screenshot) {
    const destination = 'https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml';
    const link = p.getByRole('link', { name: 'Suggest a welcoming jar', exact: true });
    assert.equal(await link.count(), 1);
    assert.equal(await link.isVisible(), true);
    assert.equal(await link.getAttribute('href'), destination);
    assert.equal(await link.getAttribute('target'), null);
    assert.match(
      await link.locator('..').innerText(),
      /Coverage is partial; listing is not guaranteed/,
    );
    // Reach the actual anchor in document order; do not programmatically focus it.
    for (let tabs = 0; tabs < 60; tabs++) {
      if (await link.evaluate((e) => document.activeElement === e)) break;
      await p.keyboard.press('Tab');
    }
    assert.equal(await link.evaluate((e) => document.activeElement === e), true);
    assert.equal(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    if (screenshot) await p.screenshot({ path: path.join(output, screenshot), fullPage: true });
    // Fulfill navigation locally: this check never contacts GitHub or submits an issue.
    let navigated = false;
    await p.route(destination, (route) => {
      navigated = true;
      return route.fulfill({
        contentType: 'text/html',
        body: '<title>Local navigation check</title>',
      });
    });
    await p.keyboard.press('Enter');
    await p.waitForURL(destination);
    assert.equal(navigated, true);
    assert.equal(await p.title(), 'Local navigation check');
  }
  const ordinaryURL = 'https://github.com/nkovanen/tipjar/blob/main/docs/tipping.md#give-a-tip-with-your-existing-agent';
  async function openOrdinaryGuide(p) {
    const guide = p.getByRole('link', { name: 'How to give a tip', exact: true });
    assert.equal(await guide.count(), 1);
    assert.equal(await guide.getAttribute('href'), ordinaryURL);
    await p.route(ordinaryURL.split('#')[0], (route) => route.fulfill({
      contentType: 'text/html', body: '<title>Local guide navigation check</title>',
    }));
    await guide.focus();
    await p.keyboard.press('Enter');
    await p.waitForURL(ordinaryURL);
    assert.equal(await p.title(), 'Local guide navigation check');
  }
  try {
    for (const width of [1440, 390]) {
      const p = await page(width), requests = [];
      p.on('request', (r) => requests.push(r.url()));
      await p.goto(origin + '/tipjar/index.html');
      const step = p.locator('.steps article').filter({ has: p.getByRole('heading', { name: 'Read the room.', exact: true }) });
      assert.deepEqual(await step.locator('a').evaluateAll((links) => links.map((a) => a.href)),
        [ordinaryURL, 'https://github.com/nkovanen/tipjar#install-from-source']);
      await step.getByRole('link', { name: 'How to give a tip', exact: true }).focus();
      await p.keyboard.press('Tab');
      assert.equal(await step.getByRole('link', { name: 'Optional: CLI & Skill', exact: true })
        .evaluate((a) => a === document.activeElement), true);
      assert.equal(requests.some((url) => url.endsWith('/board.json')), false);
      assert.equal(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await p.screenshot({ path: path.join(output, `ordinary-landing-${width}.png`), fullPage: true });
      await openOrdinaryGuide(p);
      await p.close(); checks++;
      for (const state of ['manifest-welcome', 'readme-welcome']) {
        const w = await page(width, fixture('v2/' + state)), reads = [];
        w.on('request', (r) => reads.push(r.url()));
        await w.addInitScript(() => Object.defineProperty(navigator, 'clipboard', {
          configurable: true, value: { writeText: async (text) => { window.ordinaryCopied = text; } },
        }));
        await w.goto(origin + '/tipjar/leaderboard.html?repository_id=101&period=all');
        await w.locator('#board-detail[open]').waitFor();
        assert.match(await w.locator('#board-detail-content').innerText(), /Tipjar's CLI is optional/);
        assert.match(await w.locator('#board-detail-content').innerText(), /Optional CLI helper/);
        await w.getByRole('button', { name: 'Copy', exact: true }).click();
        assert.equal(await w.evaluate(() => window.ordinaryCopied), 'tipjar discover fictional-demo/welcoming-jar --signals');
        await w.getByRole('button', { name: 'Copy view link', exact: true }).click();
        assert.equal(await w.evaluate(() => window.ordinaryCopied), origin + '/tipjar/leaderboard.html?repository_id=101&period=all');
        assert.equal(reads.filter((url) => url.endsWith('/board.json')).length, 1);
        await w.screenshot({ path: path.join(output, `ordinary-${state}-${width}.png`), fullPage: true });
        await openOrdinaryGuide(w);
        await w.close(); checks++;
      }
      for (const state of ['manifest-closed', 'readme-undeclared', 'absent', 'unknown', 'missing', 'expired']) {
        const data = fixture('v2/' + (state === 'missing' ? 'readme-welcome' : state));
        if (state === 'missing') data.directory.observations = [];
        const n = await page(width, data);
        await n.goto(origin + '/tipjar/leaderboard.html?repository_id=101&period=all');
        if (state === 'expired') {
          await n.waitForFunction(() => document.getElementById('board-status').innerText.includes('overdue'));
          assert.equal(await n.locator('#board-detail[open]').count(), 0);
        } else await n.locator('#board-detail[open]').waitFor();
        assert.equal(await n.getByRole('link', { name: 'How to give a tip', exact: true }).count(), 0);
        assert.equal(await n.locator('#board-detail-content .command').count(), 0);
        assert.deepEqual(n.errors, []);
        await n.close(); checks++;
      }
    }
    for (const width of [1440, 390]) {
      const p = await page(width, fixture('v2/readme-welcome')),
        requests = [];
      p.on('request', (r) => requests.push(r.url()));
      await p.addInitScript(() => {
        Object.defineProperty(navigator, 'clipboard', {
          configurable: true,
          value: {
            writeText: async (text) => {
              window.handoffCopied = text;
            },
          },
        });
        window.handoffWrites = [];
        for (const method of ['pushState', 'replaceState']) {
          const original = history[method].bind(history);
          history[method] = (...args) => {
            window.handoffWrites.push(method);
            return original(...args);
          };
        }
      });
      await p.goto(origin + '/tipjar/?repo=fictional-demo%2Fwelcoming-jar');
      const handoff = p.getByRole('link', {
        name: 'Look for this project on the public board ↗',
        exact: true,
      });
      assert.equal(
        await handoff.getAttribute('href'),
        origin + '/tipjar/leaderboard.html?repo=fictional-demo%2Fwelcoming-jar&period=month',
      );
      assert.equal(requests.filter((u) => u.endsWith('/board.json')).length, 0);
      assert.match(
        await p.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content'),
        /connect-src 'none'/,
      );
      assert.equal(await p.locator('#repository-invitation a').count(), 2);
      await p.screenshot({ path: path.join(output, `handoff-root-${width}.png`), fullPage: true });
      await handoff.click();
      await p.locator('#repository-handoff .handoff-profile').waitFor({ timeout: 1500 });
      assert.equal(await p.locator('#board-detail').evaluate((e) => e.open), false);
      assert.match(
        await p.locator('#repository-handoff').innerText(),
        /Current public snapshot match/,
      );
      assert.match(
        await p.locator('#repository-handoff').innerText(),
        /Badge origin and earlier ownership are not verified/,
      );
      assert.equal(
        await p.locator('#handoff-title').evaluate((e) => document.activeElement === e),
        true,
      );
      assert.equal(await p.locator('#repository-handoff .command').count(), 0);
      assert.equal(
        await p.locator('#repository-handoff .handoff-profile').getAttribute('href'),
        origin + '/tipjar/leaderboard.html?repository_id=101&period=month',
      );
      await p.screenshot({ path: path.join(output, `handoff-match-${width}.png`), fullPage: true });
      await p.locator('#board-period [data-period="all"]').click();
      assert.equal(new URL(p.url()).search, '?repo=fictional-demo%2Fwelcoming-jar&period=all');
      await p.locator('#repository-handoff .handoff-profile').click();
      await p.locator('#board-detail[open]').waitFor();
      assert.equal(new URL(p.url()).search, '?repository_id=101&period=all');
      await p.getByRole('button', { name: 'Copy view link', exact: true }).click();
      assert.equal(
        await p.evaluate(() => window.handoffCopied),
        origin + '/tipjar/leaderboard.html?repository_id=101&period=all',
      );
      assert.equal(await p.locator('#repository-handoff').isVisible(), false);
      await p.screenshot({
        path: path.join(output, `handoff-numeric-${width}.png`),
        fullPage: true,
      });
      await p.evaluate(() => {
        window.handoffWrites = [];
      });
      await p.goBack();
      await p.locator('#repository-handoff .handoff-profile').waitFor();
      assert.equal(
        await p.locator('#handoff-title').evaluate((e) => document.activeElement === e),
        true,
      );
      await p.goForward();
      await p.locator('#board-detail[open]').waitFor();
      assert.deepEqual(await p.evaluate(() => window.handoffWrites), []);
      await p.keyboard.press('Escape');
      assert.equal(new URL(p.url()).search, '?period=all');
      assert.equal(
        await p.locator('#people-title').evaluate((e) => document.activeElement === e),
        true,
      );
      assert.equal(requests.filter((u) => u.endsWith('/board.json')).length, 1);
      assert.equal(
        requests.some((u) => u.includes('api.github.com')),
        false,
      );
      assert.deepEqual(p.errors, []);
      await p.close();
      checks += 10;
      for (const name of [
        'valid',
        'v2/readme-welcome',
        'v2/manifest-closed',
        'v2/unknown',
        'v2/absent',
      ]) {
        const q = await page(width, fixture(name));
        await q.goto(origin + '/tipjar/leaderboard.html?repo=FICTIONAL-DEMO%2FWELCOMING-JAR');
        await q.locator('#repository-handoff .handoff-profile').waitFor();
        assert.equal(await q.locator('#board-detail').evaluate((e) => e.open), false);
        assert.equal(await q.locator('#repository-handoff .command').count(), 0);
        assert.deepEqual(q.errors, []);
        await q.close();
        checks++;
      }
      const only = fixture('v2/readme-welcome');
      only.tips = [];
      const w = await page(width, only);
      await w.goto(origin + '/tipjar/leaderboard.html?repo=fictional-demo%2Fwelcoming-jar');
      await w.locator('#repository-handoff .handoff-profile').waitFor();
      await w.locator('#repository-handoff .handoff-profile').click();
      assert.match(
        await w.locator('#board-detail-content').innerText(),
        /No accepted tips in this period/,
      );
      await w.close();
      checks++;
      for (const data of [fixture('v2/empty'), fixture('v2/partial')]) {
        const q = await page(width, data);
        await q.goto(origin + '/tipjar/leaderboard.html?repo=missing%2Fproject');
        await q.getByRole('link', { name: 'Suggest a jar for review', exact: true }).waitFor();
        assert.match(
          await q.locator('#repository-handoff').innerText(),
          /Not listed in this snapshot/,
        );
        assert.match(await q.locator('#repository-handoff').innerText(), /Coverage is limited/);
        assert.equal(await q.locator('#repository-handoff .handoff-profile').count(), 0);
        assert.equal(
          await q
            .getByRole('link', { name: 'Suggest a jar for review', exact: true })
            .getAttribute('href'),
          'https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml',
        );
        assert.equal(
          await q
            .getByRole('link', { name: 'Prepare an invitation locally', exact: true })
            .getAttribute('href'),
          origin + '/tipjar/directory.html?repo=missing%2Fproject#maintainers',
        );
        if (!data.tips.length)
          await q.screenshot({
            path: path.join(output, `handoff-not-listed-${width}.png`),
            fullPage: true,
          });
        await q.close();
        checks++;
      }
      for (const data of [null, { format: 'future' }, fixture('v2/expired')]) {
        const q = await page(width, data);
        await q.goto(origin + '/tipjar/leaderboard.html?repo=fictional-demo%2Fwelcoming-jar');
        await q.waitForFunction(
          () =>
            document.getElementById('board-status').innerText.includes('breather') ||
            document.getElementById('board-status').innerText.includes('Refresh overdue'),
        );
        assert.match(await q.locator('#repository-handoff').innerText(), /lookup is unavailable/);
        assert.doesNotMatch(
          await q.locator('#repository-handoff').innerText(),
          /Not listed|fictional-demo/,
        );
        assert.equal(await q.locator('#repository-handoff .handoff-profile').count(), 0);
        if (data?.format === 'tipjar-board/2')
          await q.screenshot({
            path: path.join(output, `handoff-expired-${width}.png`),
            fullPage: true,
          });
        assert.deepEqual(q.errors, []);
        await q.close();
        checks++;
      }
      const x = await page(width);
      await x.goto(origin + '/tipjar/leaderboard.html?repo=fictional-demo%2Fwelcoming-jar');
      await x.locator('#repository-handoff .handoff-profile').waitFor();
      const url = x.url();
      await x.clock.setSystemTime(new Date('2026-11-05T12:00:00Z'));
      await x.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      assert.equal(x.url(), url);
      assert.equal(await x.locator('#repository-handoff .handoff-profile').count(), 0);
      assert.doesNotMatch(await x.locator('#repository-handoff').innerText(), /fictional-demo/);
      assert.equal(await x.locator('#board-detail').evaluate((e) => e.open), false);
      await x.close();
      checks++;
      for (const query of [
        'repo=a/b&repo=a/b',
        'repo=a/b&repository_id=101',
        'repo=a/b&author_id=301',
        'repo=evil%3Csvg%3E/x',
        'repo=a%252Fb',
        'repo=a/b&period=bad',
      ]) {
        const q = await page(width);
        await q.goto(origin + '/tipjar/index.html?' + query);
        assert.equal(await q.locator('#repository-invitation a').count(), 0);
        assert.doesNotMatch(await q.locator('#repository-invitation').innerText(), /evil|<svg>/);
        await q.goto(origin + '/tipjar/leaderboard.html?' + query);
        await q.locator('#people-content tbody').waitFor();
        assert.equal(await q.locator('#repository-handoff .handoff-profile').count(), 0);
        assert.equal(await q.locator('#board-detail').evaluate((e) => e.open), false);
        await q.close();
        checks++;
      }
      const renamed = fixture('v2/empty');
      renamed.repositories = [
        {
          repository_id: 888,
          repository: 'fictional-demo/new-name',
          primary_language: null,
          verified_at: renamed.generated_at,
        },
      ];
      const q = await page(width, renamed);
      await q.goto(origin + '/tipjar/leaderboard.html?repo=fictional-demo%2Fwelcoming-jar');
      await q.getByRole('link', { name: 'Suggest a jar for review', exact: true }).waitFor();
      assert.equal(await q.locator('#repository-handoff .handoff-profile').count(), 0);
      await q.close();
      checks++;
      const reused = fixture('v2/empty');
      reused.repositories = [
        {
          repository_id: 999,
          repository: 'fictional-demo/welcoming-jar',
          primary_language: null,
          verified_at: reused.generated_at,
        },
      ];
      const r = await page(width, reused);
      await r.goto(origin + '/tipjar/leaderboard.html?repo=fictional-demo%2Fwelcoming-jar');
      await r.locator('#repository-handoff .handoff-profile').waitFor();
      assert.match(
        await r.locator('#repository-handoff .handoff-profile').getAttribute('href'),
        /repository_id=999/,
      );
      assert.match(
        await r.locator('#repository-handoff').innerText(),
        /earlier ownership are not verified/,
      );
      await r.close();
      checks++;
      for (const entry of [
        'index.html?repo=fictional-demo%2Fwelcoming-jar',
        'leaderboard.html?repo=fictional-demo%2Fwelcoming-jar',
      ]) {
        const n = await browser.newPage({
            viewport: { width, height: 1000 },
            javaScriptEnabled: false,
          }),
          reads = [];
        n.on('request', (r) => reads.push(r.url()));
        await n.goto(origin + '/tipjar/' + entry);
        assert.equal(await n.locator('noscript a[href="leaderboard.html"]').isVisible(), true);
        assert.equal(
          await n.locator('noscript a[href="directory.html#maintainers"]').isVisible(),
          true,
        );
        assert.equal(
          await n
            .locator(
              'noscript a[href="https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml"]',
            )
            .isVisible(),
          true,
        );
        assert.equal(
          reads.some((u) => u.endsWith('/board.json') || u.includes('api.github.com')),
          false,
        );
        await n.close();
        checks++;
      }
    }
    for (const width of [1440, 390]) {
      for (const javaScriptEnabled of [true, false]) {
        for (const file of ['index', 'leaderboard']) {
          const context = await browser.newContext({
            viewport: { width, height: 1000 },
            javaScriptEnabled,
            reducedMotion: 'reduce',
          });
          const p = await context.newPage();
          const requests = [];
          p.on('request', (r) => requests.push(r.url()));
          await p.clock.install({ time: new Date('2026-11-03T13:00:00Z') });
          await p.route('**/tipjar/board.json', (route) =>
            route.fulfill({
              contentType: 'application/json',
              body: JSON.stringify(fixture('v2/empty')),
            }),
          );
          await p.goto(origin + '/tipjar/' + file + '.html');
          await suggestionLink(
            p,
            `suggest-${file}-${width}-${javaScriptEnabled ? 'js' : 'nojs'}.png`,
          );
          assert.equal(
            requests.filter((u) => u.endsWith('/board.json')).length,
            file === 'leaderboard' && javaScriptEnabled ? 1 : 0,
          );
          await context.close();
          checks++;
        }
      }
      for (const state of ['partial', 'expired', 'readme-welcome']) {
        const p = await page(width, fixture('v2/' + state));
        await p.goto(origin + '/tipjar/leaderboard.html');
        await p.waitForFunction(
          () => !document.getElementById('board-status').innerText.includes('Filling'),
        );
        if (state === 'expired')
          assert.equal(await p.locator('#welcome-content article').count(), 0);
        await suggestionLink(p, `suggest-${state}-${width}.png`);
        await p.close();
        checks++;
      }
    }
    for (const width of [1440, 390]) {
      const p = await page(width, fixture('v2/readme-welcome'));
      const requests = [];
      p.on('request', (r) => requests.push(r.url()));
      await p.addInitScript(() => {
        Object.defineProperty(navigator, 'clipboard', {
          configurable: true,
          value: {
            writeText: async (text) => {
              window.copiedView = text;
            },
          },
        });
        window.historyWrites = [];
        for (const method of ['pushState', 'replaceState']) {
          const original = history[method].bind(history);
          history[method] = (...args) => {
            window.historyWrites.push(method);
            return original(...args);
          };
        }
      });
      await p.goto(
        origin + '/tipjar/leaderboard.html?repository_id=101&period=all&unknown=literal#projects',
      );
      await p.locator('#board-detail[open]').waitFor({ timeout: 1500 });
      assert.equal(
        await p.locator('#board-detail-title').innerText(),
        'fictional-demo/welcoming-jar',
      );
      assert.equal(
        await p.locator('#board-detail-title').evaluate((e) => document.activeElement === e),
        true,
      );
      await p.screenshot({
        path: path.join(output, `share-repository-${width}.png`),
        fullPage: true,
      });
      await p.getByRole('button', { name: 'Copy view link', exact: true }).click();
      assert.equal(
        await p.evaluate(() => window.copiedView),
        origin + '/tipjar/leaderboard.html?repository_id=101&period=all',
      );
      assert.equal(await p.locator('#board-detail #board-share-status[role=status]').count(), 1);
      assert.match(await p.locator('#board-share-status').innerText(), /copied/);
      await p.evaluate(() => {
        navigator.clipboard.writeText = async () => {
          throw new Error('unavailable');
        };
      });
      await p.getByRole('button', { name: 'Copy view link', exact: true }).click();
      const fallback = p.locator('#board-share-link');
      assert.equal(
        await fallback.inputValue(),
        origin + '/tipjar/leaderboard.html?repository_id=101&period=all',
      );
      assert.equal(
        await fallback.evaluate(
          (e) =>
            document.activeElement === e &&
            e.selectionStart === 0 &&
            e.selectionEnd === e.value.length,
        ),
        true,
      );
      await p.screenshot({
        path: path.join(output, `share-copy-fallback-${width}.png`),
        fullPage: true,
      });
      const beforeClose = await p.evaluate(() => history.length);
      await p.keyboard.press('Escape');
      await p.waitForFunction(() => !document.getElementById('board-detail').open);
      assert.equal(new URL(p.url()).search, '?period=all');
      assert.equal(await p.evaluate(() => history.length), beforeClose);
      assert.equal(
        await p.locator('#people-title').evaluate((e) => document.activeElement === e),
        true,
      );
      const author = p.locator('#people-content a.row-button').first();
      assert.equal(
        await author.getAttribute('href'),
        origin + '/tipjar/leaderboard.html?author_id=301&period=all',
      );
      assert.equal(
        await author.evaluate((e) => {
          const event = new MouseEvent('click', { bubbles: true, cancelable: true, ctrlKey: true });
          e.dispatchEvent(event);
          return event.defaultPrevented;
        }),
        false,
      );
      await author.click();
      await p.locator('#board-detail[open]').waitFor();
      assert.equal(new URL(p.url()).search, '?author_id=301&period=all');
      await p.screenshot({
        path: path.join(output, `share-contributor-${width}.png`),
        fullPage: true,
      });
      assert.equal(await p.locator('#board-detail-content .represented-projects a').count(), 1);
      await p.evaluate(() => {
        window.historyWrites = [];
      });
      await p.goBack();
      await p.waitForFunction(() => !document.getElementById('board-detail').open);
      await p.goForward();
      await p.locator('#board-detail[open]').waitFor();
      assert.deepEqual(await p.evaluate(() => window.historyWrites), []);
      await p.locator('#board-detail-content .represented-projects a').click();
      assert.equal(new URL(p.url()).searchParams.get('repository_id'), '101');
      await p.goBack();
      await p.waitForFunction(
        () => document.getElementById('board-detail-title')?.textContent === 'fictional-giver',
      );
      await p.locator('#board-detail [data-period="month"]').click();
      assert.equal(new URL(p.url()).search, '?author_id=301&period=month');
      assert.equal(await p.locator('[data-period="month"][aria-pressed="true"]').count(), 2);
      assert.equal(
        await p
          .locator('#board-detail [data-period="month"]')
          .evaluate((e) => document.activeElement === e),
        true,
      );
      await p.getByRole('button', { name: 'Close board details' }).click();
      assert.equal(
        await p.locator('#people-title').evaluate((e) => document.activeElement === e),
        true,
        'disconnected opener returns to heading',
      );
      const project = p.locator('#projects-content a.row-button').first();
      await project.click();
      await p.getByRole('button', { name: 'Close board details' }).click();
      assert.equal(
        await project.evaluate((e) => document.activeElement === e),
        true,
        'connected opener focus restored',
      );
      await p.locator('#people-content a.row-button').first().click();
      await p.evaluate(() => {
        navigator.clipboard.writeText = () =>
          new Promise((resolve, reject) => {
            window.finishOldCopy = reject;
          });
      });
      await p.getByRole('button', { name: 'Copy view link', exact: true }).click();
      await p.keyboard.press('Escape');
      await p.locator('#projects-content a.row-button').first().click();
      await p.evaluate(() => window.finishOldCopy(new Error('late failure')));
      assert.equal(await p.locator('#board-share-link').isVisible(), false);
      assert.equal(await p.locator('#board-share-status').innerText(), '');
      await p.getByRole('button', { name: 'Close board details' }).click();
      assert.equal(requests.filter((u) => u.endsWith('/board.json')).length, 1);
      assert.equal(
        requests.some((u) => u.includes('api.github.com')),
        false,
      );
      assert.deepEqual(p.errors, []);
      await p.close();
      checks += 16;
      const old = fixture('v2/readme-welcome');
      old.tips[0].merged_at = '2026-10-01T00:00:00Z';
      const q = await page(width, old);
      await q.goto(origin + '/tipjar/leaderboard.html?author_id=301&period=month');
      await q.locator('#board-detail[open]').waitFor();
      assert.match(await q.locator('#board-detail-content').innerText(), /0 points/);
      await q.locator('#board-detail [data-period="all"]').click();
      assert.match(await q.locator('#board-detail-content').innerText(), /1 points?/);
      await q.locator('#board-detail-content .represented-projects a').click();
      await q.locator('#board-detail [data-period="month"]').click();
      assert.match(
        await q.locator('#board-detail-content').innerText(),
        /No accepted tips in this period/,
      );
      assert.equal(await q.locator('#board-detail-content .command').count(), 1);
      await q.screenshot({
        path: path.join(output, `share-no-period-tips-${width}.png`),
        fullPage: true,
      });
      await q.close();
      checks++;
      const welcomeOnly = fixture('v2/readme-welcome');
      welcomeOnly.tips = [];
      const w = await page(width, welcomeOnly);
      await w.goto(origin + '/tipjar/leaderboard.html?repository_id=101');
      await w.locator('#board-detail[open]').waitFor();
      assert.match(
        await w.locator('#board-detail-content').innerText(),
        /No accepted tips in this period/,
      );
      assert.equal(await w.locator('#board-detail-content .command').count(), 1);
      await w.screenshot({
        path: path.join(output, `share-welcome-only-${width}.png`),
        fullPage: true,
      });
      await w.close();
      checks++;
      for (const query of [
        'repository_id=999',
        'author_id=999',
        'repository_id=101&author_id=301',
        'author_id=301&author_id=301',
        'author_id=%3Cimg%20src=x%20onerror=alert(1)%3E',
        'repository_id=101&period=bad',
      ]) {
        const u = await page(width);
        await u.goto(origin + '/tipjar/leaderboard.html?' + query);
        await u.locator('#people-content tbody').waitFor();
        assert.equal(await u.locator('#board-detail').evaluate((e) => e.open), false);
        assert.match(await u.locator('#share-status').innerText(), /unavailable/);
        assert.equal(
          await u
            .locator('#share-status')
            .innerText()
            .then((s) => s.includes('999') || s.includes('<img')),
          false,
        );
        assert.match(await u.locator('#board-status').innerText(), /Fresh observations/);
        assert.equal(await u.locator('#share-status img').count(), 0);
        if (query === 'author_id=999')
          await u.screenshot({
            path: path.join(output, `share-stale-${width}.png`),
            fullPage: true,
          });
        await u.close();
        checks++;
      }
      const e = await page(width, fixture('v2/expired'));
      await e.goto(origin + '/tipjar/leaderboard.html?author_id=301');
      await e.waitForFunction(() =>
        document.getElementById('board-status').innerText.includes('Refresh overdue'),
      );
      assert.equal(await e.locator('#board-detail').evaluate((e) => e.open), false);
      assert.equal(await e.locator('#copy-board-view').isVisible(), false);
      await e.screenshot({ path: path.join(output, `share-expired-${width}.png`), fullPage: true });
      await e.close();
      checks++;
      const x = await page(width);
      await x.goto(origin + '/tipjar/leaderboard.html?author_id=301');
      await x.locator('#board-detail[open]').waitFor();
      await x.evaluate(() =>
        Object.defineProperty(navigator, 'clipboard', {
          configurable: true,
          value: {
            writeText: () =>
              new Promise((resolve, reject) => {
                window.finishExpiredCopy = reject;
              }),
          },
        }),
      );
      await x.getByRole('button', { name: 'Copy view link', exact: true }).click();
      const retained = x.url();
      await x.clock.setSystemTime(new Date('2026-11-05T12:00:00Z'));
      await x.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
      assert.equal(await x.locator('#board-detail').evaluate((e) => e.open), false);
      await x.evaluate(() => window.finishExpiredCopy(new Error('expired clipboard failure')));
      assert.equal(x.url(), retained);
      assert.equal(await x.locator('#people-content tbody').count(), 0);
      assert.equal(await x.locator('#welcome-content article').count(), 0);
      assert.equal(await x.locator('#board-detail-content').innerText(), '');
      assert.deepEqual(x.errors, []);
      await x.close();
      checks++;
    }
    for (const width of [1440, 390]) {
      const p = await page(width);
      await p.goto(origin + '/tipjar/index.html');
      assert.equal(await p.title(), 'Tipjar — a little work goes a long way');
      assert.equal(
        await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        true,
        'landing overflow ' + width,
      );
      assert.equal(
        await p
          .locator('body')
          .innerText()
          .then((x) => x.includes('®')),
        false,
      );
      await p.screenshot({
        path: path.join(output, `landing-${width}.png`),
        fullPage: true,
      });
      await p.getByRole('link', { name: 'Community board', exact: true }).click();
      await p.locator('#people-content tbody tr').waitFor();
      assert.equal(await p.locator('#people-content tbody tr').count(), 1);
      assert.equal(await p.locator('#projects-content tbody tr').count(), 1);
      assert.equal(await p.locator('#welcome-content article').count(), 1);
      assert.equal(
        await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
        true,
        'board overflow ' + width,
      );
      await p.screenshot({
        path: path.join(output, `board-${width}.png`),
        fullPage: true,
      });
      const opener = p.getByRole('link', {
        name: 'fictional-giver',
        exact: true,
      });
      await opener.click();
      await p.locator('#board-detail[open]').waitFor();
      assert.equal(
        await p.getByRole('link', { name: 'Merged pull request ↗' }).getAttribute('href'),
        'https://github.com/fictional-demo/welcoming-jar/pull/7',
      );
      assert.equal(
        await p.getByRole('link', { name: 'Public opt-in submission ↗' }).getAttribute('href'),
        'https://github.com/nkovanen/tipjar/issues/11',
      );
      await p.keyboard.press('Escape');
      await p.waitForFunction(() => !document.getElementById('board-detail').open);
      assert.equal(
        await opener.evaluate((e) => document.activeElement === e),
        true,
        'Escape restores focus',
      );
      await opener.focus();
      await p.keyboard.press('Enter');
      assert.equal(await p.locator('#board-detail').evaluate((e) => e.open), true);
      await p.getByRole('button', { name: 'Close board details' }).click();
      await p
        .getByRole('link', {
          name: 'fictional-demo/welcoming-jar',
          exact: true,
        })
        .click();
      assert.match(
        await p.locator('#board-detail-content').innerText(),
        /tipjar discover fictional-demo\/welcoming-jar --signals/,
      );
      await p.getByRole('button', { name: 'Close board details' }).click();
      await p.getByRole('button', { name: 'All time', exact: true }).click();
      assert.equal(
        await p.getByRole('button', { name: 'All time', exact: true }).getAttribute('aria-pressed'),
        'true',
      );
      await p.locator('#board-search').fill('no-such-project');
      assert.match(await p.locator('#welcome-empty').innerText(), /No jars match/);
      await p.locator('#board-search').fill('');
      await p.clock.setSystemTime(new Date('2026-11-05T12:00:00Z'));
      await p.clock.runFor(1100);
      assert.match(await p.locator('#board-status').innerText(), /Refresh overdue/);
      assert.equal(await p.locator('#people-content tbody').count(), 0);
      assert.equal(await p.locator('#welcome-content article').count(), 0);
      assert.equal(await p.locator('#explore').isVisible(), false);
      assert.deepEqual(p.errors, []);
      await p.close();
      checks += 15;
    }
    for (const name of ['empty', 'partial']) {
      const p = await page(390, fixture(name));
      await p.goto(origin + '/tipjar/leaderboard.html');
      await p.waitForFunction(
        () => !document.getElementById('board-status').innerText.includes('Filling'),
      );
      if (name === 'empty')
        assert.match(await p.locator('#people-content').innerText(), /No eligible, opted-in tips/);
      else assert.match(await p.locator('#board-status').innerText(), /partial pour/);
      await p.screenshot({
        path: path.join(output, `${name}-390.png`),
        fullPage: true,
      });
      assert.deepEqual(p.errors, []);
      await p.close();
      checks++;
    }
    const hostile = fixture('valid');
    hostile.directory.observations[0].jar.manifest.wanted = [
      '<img src=x onerror="globalThis.injected=true">',
    ];
    hostile.repositories[0].primary_language = '<script>literal</script>';
    const p = await page(390, hostile);
    await p.goto(origin + '/tipjar/leaderboard.html');
    await p.locator('#welcome-content article').waitFor();
    assert.match(await p.locator('#welcome-content').innerText(), /<img src=x/);
    assert.equal(await p.locator('#welcome-content img').count(), 0);
    assert.equal(await p.evaluate(() => globalThis.injected), undefined);
    await p.close();
    checks++;
    const closed = fixture('valid');
    closed.directory.observations[0].disposition = 'closed';
    closed.directory.observations[0].jar.state = 'closed';
    closed.directory.observations[0].jar.manifest.status = 'closed';
    const c = await page(390, closed);
    await c.goto(origin + '/tipjar/leaderboard.html');
    await c.locator('#projects-content tbody').waitFor();
    await c
      .getByRole('link', {
        name: 'fictional-demo/welcoming-jar',
        exact: true,
      })
      .click();
    assert.equal(await c.locator('#board-detail-content .command').count(), 0);
    assert.match(await c.locator('#board-detail-content').innerText(), /No new-work suggestion/);
    await c.close();
    checks++;
    for (const invalid of [null, { format: 'unknown' }]) {
      const p = await page(390, invalid);
      await p.goto(origin + '/tipjar/leaderboard.html');
      await p.waitForFunction(() =>
        document.getElementById('board-status').innerText.includes('breather'),
      );
      assert.equal(await p.locator('#people-content tbody').count(), 0);
      assert.equal(await p.locator('#welcome-content article').count(), 0);
      await p.close();
      checks++;
    }
    for (const width of [1440, 390]) {
      for (const name of [
        'manifest-welcome',
        'manifest-closed',
        'readme-welcome',
        'readme-undeclared',
        'absent',
        'unknown',
        'empty',
        'partial',
        'expired',
      ]) {
        const data = fixture('v2/' + name),
          p = await page(width, data);
        await p.goto(origin + '/tipjar/leaderboard.html');
        await p.waitForFunction(
          () => !document.getElementById('board-status').innerText.includes('Filling'),
        );
        const fresh = name !== 'expired';
        assert.equal(
          await p.locator('#welcome-content article').count(),
          fresh ? data.directory.observations.filter((o) => o.disposition === 'welcome').length : 0,
        );
        assert.equal(
          await p.locator('#people-content tbody tr').count(),
          fresh && data.tips.length ? 1 : 0,
        );
        assert.equal(
          await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
          true,
          'board2 overflow ' + name + '/' + width,
        );
        if (name === 'expired')
          assert.match(await p.locator('#board-status').innerText(), /Refresh overdue/);
        else if (name === 'partial' || name === 'unknown')
          assert.match(await p.locator('#board-status').innerText(), /partial pour/);
        if (fresh && data.tips.length) {
          await p.locator('#projects-content a.row-button').first().click();
          const observation = data.directory.observations[0],
            expectedFile =
              observation.source?.kind === 'readme'
                ? 'README.md'
                : observation.source?.kind === 'manifest'
                  ? '.tipjar.json'
                  : null;
          const fileLinks = p.locator('#board-detail-content')
            .getByRole('link', { name: /^Pinned (README|invitation) source ↗$/ });
          assert.equal(await fileLinks.count(), expectedFile ? 1 : 0);
          if (expectedFile)
            assert.equal(
              await fileLinks.getAttribute('href'),
              `https://github.com/${observation.repository}/blob/${observation.source.commit}/${expectedFile}`,
            );
          assert.equal(
            await p.locator('#board-detail-content .command').count(),
            observation.disposition === 'welcome' ? 1 : 0,
          );
          if (observation.source?.kind === 'readme')
            assert.match(await p.locator('#board-detail-content').innerText(), /README/);
          await p.keyboard.press('Escape');
          await p.waitForFunction(() => !document.getElementById('board-detail').open);
        }
        await p.screenshot({
          path: path.join(output, `board2-${name}-${width}.png`),
          fullPage: true,
        });
        if (name === 'readme-welcome') {
          await p.locator('#projects-content a.row-button').first().click();
          await p.screenshot({
            path: path.join(output, `board2-readme-detail-${width}.png`),
            fullPage: true,
          });
          await p.clock.setSystemTime(new Date(data.expires_at));
          await p.clock.runFor(1100);
          assert.equal(await p.locator('#board-detail').evaluate((e) => e.open), false);
          assert.equal(await p.locator('#welcome-content article').count(), 0);
          assert.equal(await p.locator('#people-content tbody').count(), 0);
        }
        assert.deepEqual(p.errors, []);
        await p.close();
        checks++;
      }
      const data = fixture('v2/manifest-welcome');
      data.directory.observations[0].jar.manifest.wanted = [
        '<img src=x onerror="globalThis.injected=true">',
      ];
      const p = await page(width, data);
      await p.goto(origin + '/tipjar/leaderboard.html');
      await p.locator('#welcome-content article').waitFor();
      assert.match(await p.locator('#welcome-content').innerText(), /<img src=x/);
      assert.equal(await p.locator('#welcome-content img').count(), 0);
      assert.equal(await p.evaluate(() => globalThis.injected), undefined);
      await p.screenshot({
        path: path.join(output, `board2-hostile-${width}.png`),
        fullPage: true,
      });
      assert.deepEqual(p.errors, []);
      await p.close();
      checks++;
    }
    const directory = await page();
    await directory.goto(origin + '/tests/web/browser.html');
    await directory.waitForFunction(
      () => /BROWSER ASSERTIONS PASSED|FAIL:/.test(document.getElementById('results').innerText),
      null,
      { timeout: 20000 },
    );
    const report = await directory.locator('#results').innerText();
    fs.writeFileSync(path.join(output, 'local-directory.txt'), report);
    assert.ok(!report.includes('FAIL'), report);
    await directory.close();
    checks++;
    console.log(
      `PASS ${checks} browser checks; desktop/390px screenshots and local directory report in ${output}`,
    );
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
