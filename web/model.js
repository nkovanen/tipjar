/* Pure data boundaries, shared by the browser and dependency-free Node tests. */
(function (root) {
  'use strict';
  const MAX_BYTES = 1048576;
  const repoPattern = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/;
  const bytes = text => new TextEncoder().encode(text).length;
  const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
  function requireValue(condition, message) { if (!condition) throw new Error(message); }
  function texts(value) {
    requireValue(Array.isArray(value) && value.length <= 16, 'Use at most 16 lines per field.');
    requireValue(value.every(x => typeof x === 'string' && [...x].length >= 1 && [...x].length <= 500 && ![...x].some(c => c.length === 1 && /[\ud800-\udfff]/u.test(c)) && !/^[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*$/u.test(x) && !/[\u0000-\u001f\u007f]/u.test(x)), 'Each line needs 1–500 characters, without control characters.');
    requireValue(new Set(value).size === value.length, 'Each line must be distinct.');
    return value.slice();
  }
  function validateManifest(value) {
    requireValue(object(value) && Object.keys(value).every(k => ['schema_version','status','wanted','boundaries'].includes(k)), 'Unknown manifest field.');
    requireValue(value.schema_version === '0.1', 'Only manifest schema 0.1 is supported.');
    requireValue(['welcome','closed'].includes(value.status), 'Choose welcome or closed.');
    const result = {schema_version:'0.1', status:value.status};
    for (const key of ['wanted','boundaries']) if (Object.hasOwn(value,key)) result[key] = texts(value[key]);
    requireValue(bytes(JSON.stringify(result)) <= 16384, 'Manifest exceeds 16 KiB.');
    return result;
  }
  function parseSnapshot(text) {
    requireValue(typeof text === 'string' && bytes(text) <= MAX_BYTES, 'Choose a JSON file of at most 1 MiB.');
    let value;
    try { value = JSON.parse(text); } catch { throw new Error('This file is not valid JSON.'); }
    requireValue(object(value) && ['find-jars-report/1','find-jars-report/2'].includes(value.format), 'Expected format find-jars-report/1 or /2.');
    requireValue(Array.isArray(value.observations) && value.observations.length <= 200 && typeof value.complete === 'boolean', 'Expected at most 200 observations and a complete flag.');
    const errors = value.errors === undefined ? [] : value.errors;
    requireValue(Array.isArray(errors) && errors.length <= 200 && errors.every(x => typeof x === 'string' && [...x].length <= 500), 'Invalid bounded search diagnostics.');
    if (value.coverage !== undefined) requireValue(object(value.coverage) && value.coverage.exhaustive === false, 'Find coverage must be non-exhaustive.');
    let skippedUnidentifiable = 0;
    const seen = new Set();
    const reports = value.observations.map((observation, index) => {
      const prefix = `Repository ${index + 1}: `;
      requireValue(object(observation), prefix + 'invalid observation.');
      requireValue(['welcome','closed','undeclared','excluded','unknown'].includes(observation.disposition), prefix + 'invalid disposition.');
      requireValue(observation.jar == null || object(observation.jar), prefix + 'jar must be an object or null.');
      if (observation.repository === null) {
        requireValue(observation.repository_id === null && observation.jar === null && ['unknown','excluded'].includes(observation.disposition)
          && typeof observation.reason === 'string' && [...observation.reason].length <= 300
          && (observation.verified_at === null || typeof observation.verified_at === 'string' && observation.verified_at.length <= 100), prefix + 'invalid unidentifiable diagnostic.');
        // Never invent a repository or retain potentially hidden identity text.
        skippedUnidentifiable++;
        return null;
      }
      requireValue(typeof observation.repository === 'string' && repoPattern.test(observation.repository), prefix + 'invalid repository.');
      const row = observation.jar ?? {repository:observation.repository,state:'unknown',complete:false};
      requireValue(observation.jar != null || ['excluded','unknown'].includes(observation.disposition), prefix + 'missing jar report.');
      requireValue(object(row) && row.repository === observation.repository, prefix + 'wrapper and jar identities disagree.');
      requireValue(object(row) && typeof row.repository === 'string' && repoPattern.test(row.repository), prefix + 'invalid GitHub owner/repository.');
      requireValue(!seen.has(row.repository.toLowerCase()), prefix + 'duplicate repository.');
      seen.add(row.repository.toLowerCase());
      requireValue(['welcome','closed','undeclared','unknown'].includes(row.state) && typeof row.complete === 'boolean', prefix + 'invalid state or completeness.');
      for (const [key,pattern] of [['commit',/^[a-f0-9]{40}$/],['sha256',/^[a-f0-9]{64}$/]]) {
        requireValue(row[key] == null || typeof row[key] === 'string' && pattern.test(row[key]), prefix + 'invalid ' + key + '.');
      }
      const manifest = row.manifest == null ? null : validateManifest(row.manifest);
      const modern = value.format === 'find-jars-report/2';
      if (modern && observation.jar != null) {
        requireValue(Number.isSafeInteger(row.repository_id) && row.repository_id > 0 && row.repository_id === observation.repository_id, prefix + 'invalid numeric source identity.');
        requireValue(['manifest','readme','absent','unknown'].includes(row.source_kind), prefix + 'invalid source kind.');
        requireValue(typeof row.manifest_present === 'boolean' || row.manifest_present === null, prefix + 'invalid manifest presence.');
        if (row.complete) {
          requireValue(typeof row.tree_sha === 'string' && /^[a-f0-9]{40}$/.test(row.tree_sha) && typeof row.commit === 'string' && typeof row.default_branch === 'string' && row.default_branch.trim(), prefix + 'missing pinned identity.');
          requireValue(row.source_kind !== 'unknown' && row.state !== 'unknown', prefix + 'unresolved source.');
          if (row.source_kind === 'readme') {
            requireValue(row.path === 'README.md' && row.manifest_present === false && manifest === null && typeof row.sha256 === 'string' && /^[a-f0-9]{40}$/.test(row.blob_sha), prefix + 'invalid README provenance.');
            requireValue(row.state === 'undeclared' && row.badge === null || row.state === 'welcome' && object(row.badge) && Object.keys(row.badge).length === 2 && row.badge.protocol === 'readme-welcome/1' && row.badge.repository === row.repository.toLowerCase(), prefix + 'invalid README invitation.');
          } else if (row.source_kind === 'absent') requireValue(row.path === null && row.manifest_present === false && row.sha256 === null && row.blob_sha === null && manifest === null && row.badge === null && row.state === 'undeclared', prefix + 'invalid absent source.');
          else requireValue(row.path === '.tipjar.json' && row.manifest_present === true && row.badge === null && typeof row.sha256 === 'string' && /^[a-f0-9]{40}$/.test(row.blob_sha) && manifest && manifest.status === row.state, prefix + 'invalid manifest provenance.');
        }
      }
      if (row.complete && ['welcome','closed'].includes(row.state) && (!modern || row.source_kind === 'manifest')) requireValue(manifest && manifest.status === row.state, prefix + 'declaration does not match manifest.');
      if (row.complete && row.state === 'undeclared') requireValue(!manifest, prefix + 'undeclared report contains a manifest.');
      const effectiveState = row.complete ? row.state : 'unknown';
      requireValue(observation.disposition === 'excluded' || observation.disposition === effectiveState, prefix + 'disposition and jar state disagree.');
      return {repository:row.repository, state:observation.disposition, complete:row.complete, manifest, source_kind:modern ? row.source_kind : 'manifest', path:modern ? row.path : '.tipjar.json', commit:row.commit || null, sha256:row.sha256 || null};
    });
    return {reports:reports.filter(row => row !== null),complete:value.complete,skippedUnidentifiable,errors:errors.slice()};
  }
  function sourceURL(row) {
    return repoPattern.test(row.repository) && typeof row.commit === 'string' && /^[a-f0-9]{40}$/.test(row.commit)
      ? `https://github.com/${row.repository}/blob/${row.commit}/${row.path === 'README.md' ? 'README.md' : '.tipjar.json'}` : null;
  }
  function filterReports(rows, query, state) {
    query = query.trim().toLowerCase();
    return rows.filter(row => (state === 'all' || state === row.state) && [row.repository,...(row.manifest?.wanted || []),...(row.manifest?.boundaries || [])].join(' ').toLowerCase().includes(query));
  }
  function makeManifest(status, wanted, boundaries) {
    requireValue(typeof wanted === 'string' && typeof boundaries === 'string' && wanted.length <= 32768 && boundaries.length <= 32768, 'Editor fields are limited to 32768 input units; shorten the text.');
    const lines = text => text.split(/\r?\n/).filter(x => x.length > 0);
    const result = validateManifest({schema_version:'0.1',status,wanted:lines(wanted),boundaries:lines(boundaries)});
    requireValue(bytes(JSON.stringify(result,null,2)+'\n') <= 16384, 'Downloaded manifest exceeds 16 KiB. Shorten the lists.');
    return result;
  }
  function makeBadge(repository) {
    requireValue(typeof repository === 'string' && repoPattern.test(repository), 'Enter a GitHub owner/repo.');
    return '<!-- tipjar:welcome:v1 -->\n[![Agent-work tips welcome](https://nkovanen.github.io/tipjar/brand/agent-work-welcome.svg)](https://nkovanen.github.io/tipjar/?repo=' + encodeURIComponent(repository.toLowerCase()) + ')\n\n';
  }
  function parseRepositoryHandoff(search) {
    const inert = {repository:null,period:'month',invalid:true};
    if (typeof search !== 'string' || search.length > 2048) return inert;
    const params = new URLSearchParams(search);
    if ([...params].length > 16 || params.has('repository_id') || params.has('author_id')) return inert;
    for (const key of ['repo','period']) if (params.getAll(key).length > 1) return inert;
    const period = params.get('period') ?? 'month';
    if (!['month','30days','all'].includes(period)) return inert;
    if (!params.has('repo')) return {repository:null,period,invalid:false};
    const repository = params.get('repo');
    if (!repoPattern.test(repository) || /[\u0000-\u0020\u007f]/u.test(repository)) return inert;
    return {repository:repository.toLowerCase(),period,invalid:false};
  }
  function repositoryHandoffURL(locationHref, entry) {
    requireValue(object(entry) && Object.keys(entry).length === 3 && ['repository','period','invalid'].every(k=>Object.hasOwn(entry,k)) && typeof entry.repository === 'string' && typeof entry.period === 'string' && entry.invalid === false,'Invalid repository handoff.');
    const parsed = parseRepositoryHandoff(new URLSearchParams({repo:entry.repository,period:entry.period}).toString());
    requireValue(!parsed.invalid && parsed.repository === entry.repository && parsed.period === entry.period,'Invalid repository handoff.');
    const url = new URL('leaderboard.html',locationHref);
    requireValue(['http:','https:'].includes(url.protocol),'Invalid board location.');
    url.search = new URLSearchParams({repo:entry.repository,period:entry.period}).toString();
    return url.href;
  }
  const api = {parseRepositoryHandoff,repositoryHandoffURL,makeBadge,MAX_BYTES,parseSnapshot,sourceURL,filterReports,makeManifest};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TipjarModel = api;
})(globalThis);
