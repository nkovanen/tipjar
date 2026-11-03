'use strict';
const boardModel = TipjarBoard,
  byId = (id) => document.getElementById(id);
let board = null,
  period = 'month',
  expired = false,
  lastOpener = null;
function node(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}
function link(text, url) {
  const n = node('a', text);
  n.href = url;
  n.rel = 'noopener noreferrer';
  return n;
}
function button(text, action, cls) {
  const n = node('button', text, cls);
  n.type = 'button';
  n.addEventListener('click', () => action(n));
  return n;
}
const date = (s) =>
  new Date(s).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }) + ' UTC';
function empty(target, title, text, action) {
  const box = node('div', undefined, 'board-empty'),
    img = node('img');
  img.src = 'brand/icon.svg';
  img.alt = '';
  box.append(img, node('h3', title), node('p', text));
  if (action) box.append(link(action[0], action[1]));
  target.replaceChildren(box);
}
function showStatus(title, text, overdue = false) {
  const box = byId('board-status');
  box.classList.toggle('overdue', overdue);
  box.replaceChildren(node('strong', title), node('p', text));
}
function hideCurrent(title, text) {
  byId('freshness').textContent = board
    ? `Last checked ${date(board.generated_at)} · expired ${date(board.expires_at)}`
    : 'No current public snapshot.';
  showStatus(title, text, true);
  for (const id of ['people-content', 'projects-content'])
    empty(
      byId(id),
      'A fresh pour is on its way.',
      'Current scores will appear after a successful refresh.',
    );
  byId('welcome-content').replaceChildren();
  empty(
    byId('welcome-empty'),
    'Welcomes are waiting for a fresh check.',
    'You can still draft your own invitation or open a local snapshot.',
    ['Open local directory tools ↗', 'directory.html'],
  );
  byId('explore').hidden = true;
  byId('people-summary').textContent = '';
  byId('newcomers').textContent = '';
  byId('directory-summary').textContent = 'Current welcome actions are unavailable.';
  if (byId('board-detail').open) byId('board-detail').close();
}
function ensureFresh() {
  if (!board || !boardModel.fresh(board)) {
    if (board && !expired) {
      expired = true;
      hideCurrent(
        'Refresh overdue',
        'The snapshot has expired. Scores and current welcome actions are hidden until a successful refresh.',
      );
    }
    return false;
  }
  return true;
}
function proofs(body, tips) {
  for (const t of tips.slice().sort((a, b) => Date.parse(b.merged_at) - Date.parse(a.merged_at))) {
    const repo = board.repositories.find((r) => r.repository_id === t.repository_id),
      box = node('article', undefined, 'proof');
    box.append(
      node('strong', `${repo.repository} #${t.number}`),
      node('p', `Merged ${date(t.merged_at)} · assistance self-declared`),
    );
    const links = node('div', undefined, 'proof-links');
    links.append(
      link('Merged pull request ↗', `https://github.com/${repo.repository}/pull/${t.number}`),
      link('Public opt-in submission ↗', t.submission_url),
    );
    box.append(links);
    if (Object.values(t.size).some((x) => x !== null))
      box.append(
        node(
          'p',
          `Size context only: +${t.size.additions ?? 'unknown'} / −${t.size.deletions ?? 'unknown'} · ${t.size.changed_files ?? 'unknown'} files. Not a score.`,
        ),
      );
    body.append(box);
  }
}
function openDetail(title, opener, render) {
  if (!ensureFresh()) return;
  lastOpener = opener;
  const body = byId('board-detail-content'),
    heading = node('h2', title);
  heading.id = 'board-detail-title';
  body.replaceChildren(heading);
  render(body);
  byId('board-detail').showModal();
}
function command(body, text) {
  const box = node('div', undefined, 'command'),
    code = node('code', text);
  box.append(
    code,
    button('Copy', async () => {
      if (!ensureFresh()) return;
      try {
        await navigator.clipboard.writeText(text);
        byId('board-toast').textContent = 'Command copied. Review it before running.';
      } catch {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        byId('board-toast').textContent = 'Command selected; use your browser copy shortcut.';
      }
    }),
  );
  body.append(box);
}
function repoDetail(repositoryId, opener) {
  const repo = board.repositories.find((r) => r.repository_id === repositoryId),
    observation = board.directory.observations.find((o) => o.repository_id === repositoryId);
  openDetail(repo.repository, opener, (body) => {
    body.append(
      link('Repository on GitHub ↗', `https://github.com/${repo.repository}`),
      node(
        'p',
        `Public metadata checked ${date(repo.verified_at)}${repo.primary_language ? ' · ' + repo.primary_language : ''}`,
      ),
    );
    if (observation) {
      body.append(
        node(
          'h3',
          observation.disposition === 'welcome'
            ? 'A current welcome'
            : 'Current declaration: ' + observation.disposition,
        ),
        node('p', `Declaration checked ${date(observation.verified_at)}.`),
      );
      for (const [key, label] of [
        ['wanted', 'Wanted work'],
        ['boundaries', 'Boundaries'],
      ])
        if (observation.jar?.manifest?.[key]?.length) {
          body.append(node('h3', label));
          const list = node('ul');
          for (const text of observation.jar.manifest[key]) list.append(node('li', text));
          body.append(list);
        }
      const source = boardModel.sourceURL(observation);
      if (source)
        body.append(
          link(
            observation.source.kind === 'readme'
              ? 'Pinned README source ↗'
              : 'Pinned invitation source ↗',
            source,
          ),
        );
      if (observation.source?.kind === 'readme')
        body.append(
          node(
            'p',
            observation.disposition === 'welcome'
              ? 'The canonical reader observed a README welcome for this repository. It grants no task, execution or publication authority.'
              : 'This README has no declared welcome. Its source pins are shown for inspection only.',
          ),
        );
      else if (observation.source?.kind === 'absent')
        body.append(
          node(
            'p',
            'No invitation file was observed at the pinned commit and tree. Absence grants no approval.',
          ),
        );
      if (observation.disposition === 'welcome') {
        command(body, `tipjar discover ${repo.repository} --signals`);
        body.append(
          node(
            'p',
            'Copying executes nothing. Read project policies, inspect an issue and get human authorization before implementation or publication.',
            'notice',
          ),
        );
      } else
        body.append(
          node(
            'p',
            'No new-work suggestion is offered from this declaration. Historical merged work is shown separately.',
            'notice',
          ),
        );
    } else
      body.append(
        node(
          'p',
          'No current invitation observation. Historical acceptance grants no permission to start new work.',
          'notice',
        ),
      );
    body.append(node('h3', 'Accepted tips in this snapshot'));
    const tips = board.tips.filter((t) => t.repository_id === repositoryId);
    if (tips.length) proofs(body, tips);
    else body.append(node('p', 'No currently counted tips.'));
  });
}
function table(target, headers, rows, makeRow) {
  const wrapper = node('div', undefined, 'table-wrap'),
    table = node('table', undefined, 'board-table'),
    caption = node('caption', headers[1] + ' rankings for the selected period', 'sr-only'),
    head = node('thead'),
    tr = node('tr');
  headers.forEach((text, i) => {
    const th = node('th', text, i === headers.length - 1 ? 'optional-column' : '');
    th.scope = 'col';
    tr.append(th);
  });
  head.append(tr);
  const body = node('tbody');
  rows.forEach((r) => body.append(makeRow(r)));
  table.append(caption, head, body);
  wrapper.append(table);
  target.replaceChildren(wrapper);
}
function cell(text, cls) {
  return node('td', text, cls);
}
function renderDirectory() {
  if (!ensureFresh()) return;
  const query = byId('board-search').value.trim().toLowerCase(),
    all = boardModel.welcoming(board),
    rows = all.filter((o) =>
      [o.repository, ...(o.jar?.manifest?.wanted || []), ...(o.jar?.manifest?.boundaries || [])]
        .join(' ')
        .toLowerCase()
        .includes(query),
    );
  byId('directory-summary').textContent =
    `${rows.length} of ${all.length} observed welcomes · bounded indexed batch, never exhaustive.`;
  byId('welcome-content').replaceChildren();
  byId('welcome-empty').replaceChildren();
  for (const o of rows) {
    const card = node('article', undefined, 'card'),
      top = node('div', undefined, 'card-top');
    top.append(node('span', '⌘', 'repo-icon'), node('span', 'Welcome', 'badge'));
    const tags = node('div', undefined, 'tags');
    for (const work of o.jar.manifest?.wanted || []) tags.append(node('span', work, 'tag'));
    const bottom = node('div', undefined, 'card-bottom');
    bottom.append(
      node(
        'span',
        board.repositories.find((r) => r.repository_id === o.repository_id)?.primary_language ||
          'Public project',
      ),
      button('Explore jar ↗', (opener) => repoDetail(o.repository_id, opener)),
    );
    card.append(top, node('h3', o.repository), tags, bottom);
    byId('welcome-content').append(card);
  }
  if (!rows.length)
    empty(
      byId('welcome-empty'),
      query ? 'No jars match this search.' : 'Make your welcome visible.',
      query
        ? 'Try another project name or kind of work.'
        : 'No verified welcoming jars in this bounded batch. A project can put out its own jar to invite thoughtful contributions.',
      query ? null : ['Draft your invitation ↗', 'directory.html#maintainers'],
    );
}
function render() {
  if (!ensureFresh()) return;
  const ranks = boardModel.rankBoard(board, period);
  byId('freshness').textContent =
    `Checked ${date(board.generated_at)} · expires ${date(board.expires_at)}`;
  showStatus(
    board.coverage.partial ? 'A partial pour.' : 'Fresh observations.',
    'Curated opt-ins and one bounded discovery batch. ' +
      (board.coverage.partial
        ? 'Some observations could not be included; totals can decrease.'
        : 'Coverage is always partial, even when this batch completes.'),
  );
  byId('people-summary').textContent =
    `${ranks.people.length} people · ${ranks.people.reduce((n, p) => n + p.points, 0)} accepted tips`;
  if (ranks.people.length)
    table(
      byId('people-content'),
      ['Rank', 'Contributor', 'Points', 'Projects', 'Milestones'],
      ranks.people,
      (p) => {
        const tr = node('tr'),
          who = cell();
        who.append(
          button(
            p.author_login,
            (opener) =>
              openDetail(p.author_login, opener, (body) => {
                body.append(
                  node('p', `${p.points} points · ${p.projects} projects in the selected period.`),
                  node('p', 'Curated public opt-in, not verified AI use.', 'notice'),
                );
                proofs(body, p.accepted);
              }),
            'row-button',
          ),
        );
        who.append(
          node(
            'span',
            p.newcomer
              ? 'First currently counted merge in this period'
              : 'A little work, given back',
            'row-meta',
          ),
        );
        tr.append(
          cell(String(p.rank)),
          who,
          cell(String(p.points), 'numeric'),
          cell(String(p.projects)),
          cell(
            p.milestones.map((n) => (n === 1 ? 'First tip' : n + ' tips')).join(' · '),
            'optional-column',
          ),
        );
        return tr;
      },
    );
  else
    empty(
      byId('people-content'),
      'The first little tip starts something.',
      'No eligible, opted-in tips in this period yet. Have a merged, agent-assisted contribution? Share your own tip for review.',
      [
        'Submit a merged tip ↗',
        'https://github.com/nkovanen/tipjar/issues/new?template=submit-tip.yml',
      ],
    );
  byId('newcomers').textContent = ranks.people.filter((p) => p.newcomer).length
    ? `${ranks.people.filter((p) => p.newcomer).length} newcomers · first currently counted merge falls in this period.`
    : '';
  if (ranks.projects.length)
    table(
      byId('projects-content'),
      ['Rank', 'Project', 'Tips', 'Contributors', 'Latest merge'],
      ranks.projects,
      (r) => {
        const tr = node('tr'),
          who = cell();
        who.append(
          button(r.repository, (opener) => repoDetail(r.repository_id, opener), 'row-button'),
          node('span', r.primary_language || 'Public repository', 'row-meta'),
        );
        tr.append(
          cell(String(r.rank)),
          who,
          cell(String(r.tips), 'numeric'),
          cell(String(r.contributors)),
          cell(date(r.latest_merge), 'optional-column'),
        );
        return tr;
      },
    );
  else
    empty(
      byId('projects-content'),
      'Useful work will find a home.',
      'Projects appear here when eligible tips are accepted into this curated pilot. Explore a welcoming jar below.',
    );
  const explored = boardModel.explore(board);
  byId('explore').hidden = !explored.length;
  byId('explore-links').replaceChildren(
    ...explored.map((o) =>
      button(o.repository + ' ↗', (opener) => repoDetail(o.repository_id, opener)),
    ),
  );
  renderDirectory();
  byId('coverage-detail').textContent =
    Object.entries(board.coverage)
      .filter(([k]) => !['exhaustive', 'partial'].includes(k))
      .map(([k, v]) => k.replaceAll('_', ' ') + ': ' + v)
      .join(' · ') +
    `. Discovery: ${board.directory.complete ? 'batch complete' : 'batch incomplete'}${board.directory.search_failed ? ' · search failed' : ''}${board.directory.server_incomplete ? ' · server incomplete' : ''}${board.directory.truncated ? ' · truncated' : ''}. Source commit: ${board.source_commit}.`;
}
byId('close-board-detail').addEventListener('click', () => byId('board-detail').close());
byId('board-detail').addEventListener('close', () => lastOpener?.focus());
byId('board-search').addEventListener('input', renderDirectory);
for (const control of document.querySelectorAll('[data-period]'))
  control.addEventListener('click', () => {
    period = control.dataset.period;
    for (const n of document.querySelectorAll('[data-period]'))
      n.setAttribute('aria-pressed', String(n === control));
    render();
  });
async function load() {
  const abort = new AbortController(),
    timeout = setTimeout(() => abort.abort(), 15000);
  let reader;
  try {
    const response = await fetch('board.json', {
      credentials: 'omit',
      redirect: 'error',
      cache: 'no-store',
      signal: abort.signal,
    });
    if (!response.ok || !response.body) throw new Error('No public snapshot');
    reader = response.body.getReader();
    const chunks = [];
    let size = 0;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > boardModel.MAX_BYTES) throw new Error('Oversized snapshot');
      chunks.push(value);
    }
    const data = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      data.set(chunk, offset);
      offset += chunk.length;
    }
    board = boardModel.parseBoard(new TextDecoder('utf-8', { fatal: true }).decode(data));
    render();
  } catch {
    if (reader) await reader.cancel().catch(() => {});
    hideCurrent(
      'The board is taking a breather.',
      'A current snapshot is unavailable. No scores or verified welcomes are shown. You can still put out a jar or submit a merged tip for review.',
    );
  } finally {
    clearTimeout(timeout);
  }
}
setInterval(() => {
  ensureFresh();
}, 1000);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) ensureFresh();
});
load();
