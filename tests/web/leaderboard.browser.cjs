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
    const file = path.resolve(root, '.' + url.pathname.replace(/^\/tipjar/, '/web'));
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
  try {
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
          const fileLinks = p.locator('#board-detail-content a[href*="/blob/"]');
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
