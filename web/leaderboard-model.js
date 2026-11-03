/* Closed public projection. No totals, URLs or invitations are trusted before validation. */
(function (root) {
  "use strict";
  const local =
    typeof module !== "undefined" && module.exports
      ? require("./model")
      : root.TipjarModel;
  const MAX_BYTES = 4 * 1024 * 1024,
    DAY = 86400000000n;
  const bytes = (s) => new TextEncoder().encode(s).length;
  function need(ok) {
    if (!ok)
      throw new Error(
        "Snapshot does not match the supported public board contract.",
      );
  }
  const obj = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
  function keys(x, list) {
    need(
      obj(x) &&
        Object.keys(x).length === list.length &&
        list.every((k) => Object.hasOwn(x, k)),
    );
  }
  const uint = (x) => Number.isSafeInteger(x) && x >= 0;
  const id = (x) => uint(x) && x > 0;
  const hex = (x, n) =>
    typeof x === "string" && new RegExp("^[0-9a-f]{" + n + "}$").test(x);
  const repo = (x) =>
    typeof x === "string" &&
    /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$/.test(x);
  const login = (x) =>
    typeof x === "string" && /^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/.test(x);
  const text = (x, n) =>
    typeof x === "string" &&
    [...x].length >= 1 &&
    [...x].length <= n &&
    !/[\u0000-\u001f\u007f]/u.test(x);
  const nonblank = (x) =>
    typeof x === "string" &&
    !/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*$/u.test(
      x,
    );
  function time(s) {
    need(
      typeof s === "string" &&
        /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z$/.test(s),
    );
    const base = s.slice(0, 19),
      ms = Date.parse(base + "Z");
    need(
      Number(s.slice(0, 4)) >= 1 &&
        Number.isFinite(ms) &&
        new Date(ms).toISOString().slice(0, 19) === base,
    );
    return (
      BigInt(ms) * 1000n +
      BigInt((s.split(".")[1]?.slice(0, -1) || "").padEnd(6, "0"))
    );
  }
  const nowTime = (now) => {
    need(now instanceof Date && Number.isFinite(now.getTime()));
    return BigInt(now.getTime()) * 1000n;
  };
  const minimum = (values) => values.reduce((a, b) => (a < b ? a : b));
  /* Scan before JSON.parse so escaped duplicate keys cannot overwrite an earlier value. */
  function strictJSON(s) {
    let i = 0;
    const ws = () => {
      while (/[\x20\t\n\r]/.test(s[i] || "!")) i++;
    };
    function string() {
      const start = i++;
      while (i < s.length) {
        const c = s[i++];
        if (c === '"') return JSON.parse(s.slice(start, i));
        if (c === "\\") i++;
      }
      throw new Error("Invalid JSON.");
    }
    function value(depth) {
      need(depth <= 32);
      ws();
      const c = s[i];
      if (c === "{" || c === "[") {
        const object = c === "{",
          end = object ? "}" : "]",
          seen = new Set();
        i++;
        ws();
        if (s[i] === end) {
          i++;
          return;
        }
        while (i < s.length) {
          if (object) {
            need(s[i] === '"');
            const k = string();
            need(!seen.has(k));
            seen.add(k);
            ws();
            need(s[i++] === ":");
          }
          value(depth + 1);
          ws();
          if (s[i] === end) {
            i++;
            return;
          }
          need(s[i++] === ",");
          ws();
        }
        need(false);
      } else if (c === '"') string();
      else {
        const match = s
          .slice(i)
          .match(
            /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/,
          );
        need(match);
        // Supported board versions have no floating fields; preserve Python's strict integer token boundary.
        need(!/^-?[0-9]/.test(match[0]) || !/[.eE]/.test(match[0]));
        i += match[0].length;
      }
    }
    value(0);
    ws();
    need(i === s.length);
    const result = JSON.parse(s);
    function unicode(x) {
      if (typeof x === "string")
        need(![...x].some((c) => c.length === 1 && /[\ud800-\udfff]/u.test(c)));
      else if (x && typeof x === "object")
        for (const [k, v] of Object.entries(x)) {
          unicode(k);
          unicode(v);
        }
    }
    unicode(result);
    return result;
  }
  function validateBoard2Observation(o, generated) {
    const j = o.jar;
    keys(j, [
      "repository",
      "repository_id",
      "default_branch",
      "commit",
      "tree_sha",
      "manifest_present",
      "source_kind",
      "path",
      "blob_sha",
      "sha256",
      "fetched_at",
      "state",
      "complete",
      "manifest",
      "badge",
      "errors",
      "notice",
    ]);
    need(
      j.repository === o.repository &&
        j.repository_id === o.repository_id &&
        j.state === o.disposition &&
        j.complete === true &&
        hex(j.commit, 40) &&
        hex(j.tree_sha, 40) &&
        text(j.default_branch, 1024) &&
        nonblank(j.default_branch) &&
        nonblank(j.notice) &&
        [...j.notice].length <= 500 &&
        Array.isArray(j.errors) &&
        j.errors.length === 0,
    );
    need(typeof j.fetched_at === "string" && j.fetched_at.length <= 100);
    need(time(j.fetched_at.replace(/\+00:00$/, "Z")) <= generated);
    if (j.source_kind === "manifest") {
      need(
        j.manifest_present === true &&
          j.path === ".tipjar.json" &&
          ["welcome", "closed"].includes(j.state) &&
          j.badge === null &&
          hex(j.blob_sha, 40) &&
          hex(j.sha256, 64),
      );
      // Manifest validation is unchanged; the canonical reader alone recognizes README invitations.
      local.parseSnapshot(
        JSON.stringify({
          format: "find-jars-report/1",
          complete: true,
          observations: [
            { repository: o.repository, disposition: o.disposition, jar: j },
          ],
        }),
      );
    } else if (j.source_kind === "readme") {
      need(
        j.manifest_present === false &&
          j.path === "README.md" &&
          j.manifest === null &&
          hex(j.blob_sha, 40) &&
          hex(j.sha256, 64),
      );
      if (j.state === "welcome") {
        keys(j.badge, ["protocol", "repository"]);
        need(
          j.badge.protocol === "readme-welcome/1" &&
            j.badge.repository === j.repository.toLowerCase(),
        );
      } else need(j.state === "undeclared" && j.badge === null);
    } else {
      need(
        j.source_kind === "absent" &&
          j.manifest_present === false &&
          j.state === "undeclared" &&
          j.manifest === null &&
          j.badge === null &&
          j.path === null &&
          j.blob_sha === null &&
          j.sha256 === null,
      );
    }
    keys(o.source, [
      "kind",
      "path",
      "commit",
      "tree_sha",
      "blob_sha",
      "sha256",
    ]);
    need(
      o.source.kind === j.source_kind &&
        ["path", "commit", "tree_sha", "blob_sha", "sha256"].every(
          (k) => o.source[k] === j[k],
        ),
    );
  }
  function parseBoard(s, now = new Date()) {
    need(typeof s === "string" && bytes(s) <= MAX_BYTES);
    const b = strictJSON(s);
    keys(b, [
      "format",
      "generated_at",
      "expires_at",
      "rules_version",
      "source_commit",
      "coverage",
      "tips",
      "repositories",
      "directory",
    ]);
    need(
      ["tipjar-board/1", "tipjar-board/2"].includes(b.format) &&
        b.rules_version === 1 &&
        hex(b.source_commit, 40),
    );
    const generated = time(b.generated_at);
    need(generated <= nowTime(now));
    const reads = [];
    function checked(s) {
      const t = time(s);
      need(t <= generated);
      reads.push(t);
      return t;
    }
    const c = b.coverage;
    keys(c, [
      "exhaustive",
      "partial",
      "unknown_tips",
      "unknown_repositories",
      "excluded_tips",
      "excluded_repositories",
      "omitted_tips",
      "omitted_repositories",
      "omitted_directory_observations",
    ]);
    need(c.exhaustive === false && typeof c.partial === "boolean");
    for (const k of Object.keys(c).slice(2)) need(uint(c[k]));
    need(Array.isArray(b.repositories) && b.repositories.length <= 200);
    const repos = new Map(),
      names = new Map();
    for (const r of b.repositories) {
      keys(r, [
        "repository_id",
        "repository",
        "primary_language",
        "verified_at",
      ]);
      need(
        id(r.repository_id) &&
          repo(r.repository) &&
          !repos.has(r.repository_id) &&
          !names.has(r.repository.toLowerCase()) &&
          (r.primary_language === null || text(r.primary_language, 100)),
      );
      repos.set(r.repository_id, r);
      names.set(r.repository.toLowerCase(), r.repository_id);
      checked(r.verified_at);
    }
    need(Array.isArray(b.tips) && b.tips.length <= 500);
    const prs = new Set(),
      numbers = new Set(),
      authors = new Map(),
      logins = new Map();
    for (const t of b.tips) {
      keys(t, [
        "repository_id",
        "pull_request_id",
        "number",
        "url",
        "author_id",
        "author_login",
        "merged_at",
        "checks",
        "verified_at",
        "submission_url",
        "agent_assistance",
        "size",
      ]);
      const r = repos.get(t.repository_id);
      need(
        r &&
          id(t.pull_request_id) &&
          id(t.number) &&
          id(t.author_id) &&
          login(t.author_login) &&
          t.agent_assistance === "self-declared",
      );
      need(
        t.url === `https://github.com/${r.repository}/pull/${t.number}` &&
          typeof t.submission_url === "string" &&
          /^https:\/\/github\.com\/nkovanen\/tipjar\/issues\/[1-9][0-9]{0,15}$/.test(
            t.submission_url,
          ) &&
          id(Number(t.submission_url.split("/").pop())),
      );
      need(
        !prs.has(t.pull_request_id) &&
          !numbers.has(t.repository_id + ":" + t.number),
      );
      prs.add(t.pull_request_id);
      numbers.add(t.repository_id + ":" + t.number);
      need(
        (!authors.has(t.author_id) ||
          authors.get(t.author_id) === t.author_login) &&
          (!logins.has(t.author_login.toLowerCase()) ||
            logins.get(t.author_login.toLowerCase()) === t.author_id),
      );
      authors.set(t.author_id, t.author_login);
      logins.set(t.author_login.toLowerCase(), t.author_id);
      keys(t.checks, ["consent", "controller", "repository", "pull_request"]);
      const checks = Object.values(t.checks).map(checked);
      need(
        time(t.verified_at) === minimum(checks) &&
          time(t.merged_at) <= time(t.checks.pull_request),
      );
      keys(t.size, ["additions", "deletions", "changed_files"]);
      need(Object.values(t.size).every((x) => x === null || uint(x)));
    }
    const d = b.directory;
    keys(d, [
      "complete",
      "search_failed",
      "server_incomplete",
      "truncated",
      "observations",
    ]);
    need(
      ["complete", "search_failed", "server_incomplete", "truncated"].every(
        (k) => typeof d[k] === "boolean",
      ),
    );
    need(
      Array.isArray(d.observations) &&
        d.observations.length <= 200 &&
        bytes(JSON.stringify(d)) <= 1048576,
    );
    const seen = new Set();
    for (const o of d.observations) {
      keys(o, [
        "repository_id",
        "repository",
        "disposition",
        "verified_at",
        "checks",
        "jar",
        "source",
      ]);
      need(
        id(o.repository_id) &&
          repo(o.repository) &&
          !seen.has(o.repository_id) &&
          repos.get(o.repository_id)?.repository === o.repository,
      );
      seen.add(o.repository_id);
      need(
        ["welcome", "closed", "undeclared", "unknown", "excluded"].includes(
          o.disposition,
        ) &&
          Array.isArray(o.checks) &&
          o.checks.length >= 2 &&
          o.checks.length <= 32,
      );
      const checks = o.checks.map(checked);
      need(time(o.verified_at) === minimum(checks));
      if (["unknown", "excluded"].includes(o.disposition))
        need(o.jar === null && o.source === null);
      else if (b.format === "tipjar-board/2")
        validateBoard2Observation(o, generated);
      else {
        const j = o.jar;
        keys(j, [
          "repository",
          "default_branch",
          "commit",
          "path",
          "blob_sha",
          "sha256",
          "fetched_at",
          "state",
          "complete",
          "manifest",
          "errors",
          "notice",
        ]);
        need(
          j.repository === o.repository &&
            j.path === ".tipjar.json" &&
            j.state === o.disposition &&
            j.complete === true &&
            hex(j.commit, 40) &&
            text(j.default_branch, 1024) &&
            nonblank(j.default_branch) &&
            nonblank(j.notice) &&
            [...j.notice].length <= 500 &&
            Array.isArray(j.errors) &&
            j.errors.length === 0,
        );
        need(typeof j.fetched_at === "string" && j.fetched_at.length <= 100);
        need(time(j.fetched_at.replace(/\+00:00$/, "Z")) <= generated);
        if (j.state === "undeclared")
          need(
            j.manifest === null &&
              j.blob_sha === null &&
              j.sha256 === null &&
              o.source === null,
          );
        else need(hex(j.blob_sha, 40) && hex(j.sha256, 64));
        // Reuse the local manifest validator only after the board envelope is closed.
        local.parseSnapshot(
          JSON.stringify({
            format: "find-jars-report/1",
            complete: true,
            observations: [
              { repository: o.repository, disposition: o.disposition, jar: j },
            ],
          }),
        );
        if (o.source !== null) {
          keys(o.source, ["kind", "path", "commit", "sha256"]);
          need(
            o.source.kind === "manifest" &&
              o.source.path === ".tipjar.json" &&
              o.source.commit === j.commit &&
              o.source.sha256 === j.sha256 &&
              hex(o.source.commit, 40) &&
              hex(o.source.sha256, 64),
          );
        }
      }
    }
    need(
      time(b.expires_at) ===
        (reads.length ? minimum(reads) : generated) + 2n * DAY,
    );
    const partial =
      Object.keys(c).some((k) => /^(unknown_|omitted_)/.test(k) && c[k] > 0) ||
      !d.complete ||
      d.search_failed ||
      d.server_incomplete ||
      d.truncated;
    need(c.partial === partial);
    need(
      !d.complete ||
        !(
          d.search_failed ||
          d.server_incomplete ||
          d.truncated ||
          d.observations.some((o) => o.disposition === "unknown")
        ),
    );
    return b;
  }
  const fresh = (b, now = new Date()) => nowTime(now) < time(b.expires_at);
  function inPeriod(t, period, now) {
    const date = time(t),
      end = nowTime(now);
    const start =
      period === "month"
        ? BigInt(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1)) * 1000n
        : period === "30days"
          ? end - 30n * DAY
          : 0n;
    return date >= start && date <= end;
  }
  function rankBoard(b, period = "month", now = new Date()) {
    need(["month", "30days", "all"].includes(period));
    if (!fresh(b, now)) return { people: [], projects: [] };
    const selected = b.tips.filter((t) => inPeriod(t.merged_at, period, now));
    const people = new Map(),
      projects = new Map();
    for (const t of selected) {
      if (!people.has(t.author_id))
        people.set(t.author_id, {
          author_id: t.author_id,
          author_login: t.author_login,
          points: 0,
          projects: new Set(),
          accepted: [],
        });
      const p = people.get(t.author_id);
      p.points++;
      p.projects.add(t.repository_id);
      p.accepted.push(t);
      if (!projects.has(t.repository_id))
        projects.set(t.repository_id, {
          ...b.repositories.find((r) => r.repository_id === t.repository_id),
          tips: 0,
          contributors: new Set(),
          latest_merge: t.merged_at,
          accepted: [],
        });
      const r = projects.get(t.repository_id);
      r.tips++;
      r.contributors.add(t.author_id);
      r.accepted.push(t);
      if (time(t.merged_at) > time(r.latest_merge))
        r.latest_merge = t.merged_at;
    }
    for (const p of people.values()) {
      const all = b.tips.filter((t) => t.author_id === p.author_id);
      p.milestones = [1, 5, 10, 25].filter((n) => all.length >= n);
      p.newcomer = inPeriod(
        all.reduce((a, t) => (time(a.merged_at) < time(t.merged_at) ? a : t))
          .merged_at,
        period,
        now,
      );
      p.projects = p.projects.size;
    }
    for (const p of projects.values()) p.contributors = p.contributors.size;
    function ranked(rows, score, identity) {
      rows.sort((a, b) => b[score] - a[score] || a[identity] - b[identity]);
      let rank = 0,
        last;
      rows.forEach((row, i) => {
        if (row[score] !== last) rank = i + 1;
        last = row[score];
        row.rank = rank;
      });
      return rows;
    }
    return {
      people: ranked([...people.values()], "points", "author_id"),
      projects: ranked([...projects.values()], "tips", "repository_id"),
    };
  }
  const welcoming = (b, now = new Date()) =>
    fresh(b, now)
      ? b.directory.observations.filter((o) => o.disposition === "welcome")
      : [];
  function explore(b, now = new Date()) {
    const rows = welcoming(b, now)
      .slice()
      .sort((a, b) => a.repository_id - b.repository_id);
    if (!rows.length) return [];
    const offset = Math.floor(now.getTime() / 86400000) % rows.length;
    return [...rows.slice(offset), ...rows.slice(0, offset)].slice(0, 3);
  }
  const sourceURL = (o) =>
    o.source && ["manifest", "readme"].includes(o.source.kind)
      ? `https://github.com/${o.repository}/blob/${o.source.commit}/${o.source.path}`
      : null;
  const periods = ["month", "30days", "all"];
  const validTarget = (target) =>
    obj(target) &&
    Object.keys(target).length === 2 &&
    ["repository", "author"].includes(target.kind) &&
    id(target.id);
  function parseBoardRoute(search) {
    const inert = { period: "month", target: null, invalid: true };
    if (typeof search !== "string" || search.length > 2048) return inert;
    const params = new URLSearchParams(search);
    if ([...params].length > 16) return inert;
    for (const key of ["repository_id", "author_id", "period"])
      if (params.getAll(key).length > 1) return inert;
    if (params.has("repository_id") && params.has("author_id")) return inert;
    const period = params.get("period") ?? "month";
    if (!periods.includes(period)) return inert;
    const key = params.has("repository_id")
      ? "repository_id"
      : params.has("author_id")
        ? "author_id"
        : null;
    if (!key) return { period, target: null, invalid: false };
    const raw = params.get(key),
      value = Number(raw);
    if (!/^[1-9][0-9]{0,15}$/.test(raw) || !id(value)) return inert;
    return {
      period,
      target: {
        kind: key === "repository_id" ? "repository" : "author",
        id: value,
      },
      invalid: false,
    };
  }
  function boardViewURL(locationHref, route) {
    keys(route, ["period", "target", "invalid"]);
    need(
      periods.includes(route.period) &&
        route.invalid === false &&
        (route.target === null || validTarget(route.target)),
    );
    const url = new URL("leaderboard.html", locationHref);
    need(["http:", "https:"].includes(url.protocol));
    if (route.target)
      url.searchParams.set(
        route.target.kind === "repository" ? "repository_id" : "author_id",
        String(route.target.id),
      );
    url.searchParams.set("period", route.period);
    return url.href;
  }
  function resolveBoardTarget(board, target, now = new Date()) {
    if (!validTarget(target) || !fresh(board, now)) return null;
    const row =
      target.kind === "repository"
        ? board.repositories.find((r) => r.repository_id === target.id)
        : board.tips.find((t) => t.author_id === target.id);
    return row
      ? {
          kind: target.kind,
          id: target.id,
          label:
            target.kind === "repository" ? row.repository : row.author_login,
        }
      : null;
  }
  const api = {
    MAX_BYTES,
    parseBoardRoute,
    boardViewURL,
    resolveBoardTarget,
    parseBoard,
    rankBoard,
    fresh,
    welcoming,
    explore,
    sourceURL,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.TipjarBoard = api;
})(globalThis);
