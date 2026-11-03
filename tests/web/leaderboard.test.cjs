"use strict";
const assert = require("node:assert/strict"),
  fs = require("node:fs"),
  test = require("node:test");
const path = "../../web/leaderboard-model";
test("public board model exists", () =>
  assert.ok(fs.existsSync(require("node:path").join(__dirname, path + ".js"))));
if (!fs.existsSync(require("node:path").join(__dirname, path + ".js"))) return;
const m = require(path),
  now = new Date("2026-11-03T13:00:00Z");
const fixture = () =>
  JSON.parse(fs.readFileSync("tests/fixtures/tipjar-board/valid.json", "utf8"));
const parse = (x) =>
  m.parseBoard(typeof x === "string" ? x : JSON.stringify(x), now);
const change = (fn) => {
  const b = fixture();
  fn(b);
  return b;
};
test("canonical empty, valid and partial fixtures", () => {
  for (const name of ["empty", "valid", "partial"])
    assert.ok(
      parse(
        fs.readFileSync(`tests/fixtures/tipjar-board/${name}.json`, "utf8"),
      ),
    );
});
test("closed fields and formats fail at every boundary", () => {
  for (const fn of [
    (b) => (b.extra = 1),
    (b) => (b.format = "future"),
    (b) => (b.coverage.extra = 1),
    (b) => (b.tips[0].extra = 1),
    (b) => (b.repositories[0].extra = 1),
    (b) => (b.directory.extra = 1),
    (b) => (b.directory.observations[0].jar.extra = 1),
    (b) => (b.directory.observations[0].source.extra = 1),
  ])
    assert.throws(() => parse(change(fn)));
});
test("duplicate decoded JSON keys rejected recursively", () => {
  const text = JSON.stringify(fixture());
  assert.throws(() =>
    parse(
      text.replace(
        '"rules_version":1',
        '"rules_version":1,"rules_\\u0076ersion":1',
      ),
    ),
  );
  assert.throws(() =>
    parse(text.replace('"additions":5', '"additions":5,"additions":5')),
  );
});
test("malformed, excessive nesting, byte cap and invalid Unicode fail", () => {
  for (const text of [
    "{",
    "[]",
    " ".repeat(4 * 1024 * 1024 + 1),
    "[".repeat(100) + "0" + "]".repeat(100),
  ])
    assert.throws(() => parse(text));
  assert.throws(() =>
    parse(change((b) => (b.repositories[0].primary_language = "\ud800"))),
  );
});
test("safe identities and canonical constructed URLs required", () => {
  for (const fn of [
    (b) => (b.tips[0].author_id = true),
    (b) => (b.repositories[0].repository_id = 9007199254740992),
    (b) => (b.tips[0].number = 0),
    (b) => (b.tips[0].url = "javascript:alert(1)"),
    (b) =>
      (b.tips[0].submission_url =
        "https://github.com/elsewhere/repo/issues/11"),
    (b) => (b.tips[0].submission_url += "?x"),
    (b) => (b.tips[0].repository_id = 999),
    (b) => (b.directory.observations[0].repository = null),
    (b) => (b.directory.observations[0].repository = "different/name"),
  ])
    assert.throws(() => parse(change(fn)));
});
test("identity conflicts and duplicate tips cannot inflate scores", () => {
  assert.throws(() => parse(change((b) => b.tips.push({ ...b.tips[0] }))));
  assert.throws(() =>
    parse(change((b) => b.repositories.push({ ...b.repositories[0] }))),
  );
  assert.throws(() =>
    parse(
      change((b) =>
        b.tips.push({
          ...b.tips[0],
          pull_request_id: 202,
          number: 8,
          url: b.tips[0].url.replace("/7", "/8"),
          author_login: "other",
        }),
      ),
    ),
  );
});
test("freshness conservative minima, calendar validity and exact expiry", () => {
  for (const fn of [
    (b) => (b.expires_at = "2026-11-06T12:00:00Z"),
    (b) => (b.generated_at = "2026-11-04T12:00:00Z"),
    (b) => (b.tips[0].checks.consent = "2026-11-03T14:00:00Z"),
    (b) => (b.tips[0].verified_at = "2026-11-03T11:00:00Z"),
    (b) => (b.tips[0].merged_at = "2026-11-04T00:00:00Z"),
    (b) => (b.repositories[0].verified_at = "2026-02-30T12:00:00Z"),
  ])
    assert.throws(() => parse(change(fn)));
  const b = change((b) => {
    b.tips[0].checks.consent = "2026-11-03T11:00:00.123456Z";
    b.tips[0].verified_at = b.tips[0].checks.consent;
    b.expires_at = "2026-11-05T11:00:00.123456Z";
  });
  assert.ok(parse(b));
  b.expires_at = "2026-11-05T11:00:00.123455Z";
  assert.throws(() => parse(b));
});
test("source links require exact pinned provenance; missing stays absent", () => {
  for (const fn of [
    (b) => (b.directory.observations[0].source.path = "README.md"),
    (b) => (b.directory.observations[0].source.commit = "e".repeat(40)),
    (b) => (b.directory.observations[0].jar.complete = false),
    (b) => (b.directory.observations[0].jar.errors = ["raw error"]),
    (b) => (b.directory.observations[0].jar.state = "closed"),
  ])
    assert.throws(() => parse(change(fn)));
  const b = parse(change((b) => (b.directory.observations[0].source = null)));
  assert.equal(m.sourceURL(b.directory.observations[0]), null);
  assert.match(
    m.sourceURL(parse(fixture()).directory.observations[0]),
    /\/blob\/b{40}\/\.tipjar.json$/,
  );
});
test("closed, unknown and expired jars never offer welcome actions", () => {
  const b = parse(fixture());
  assert.equal(m.welcoming(b, now).length, 1);
  assert.equal(m.welcoming(b, new Date("2026-11-05T12:00:00Z")).length, 0);
  for (const disposition of ["closed", "unknown", "excluded", "undeclared"]) {
    const c = fixture(),
      o = c.directory.observations[0];
    o.disposition = disposition;
    if (disposition === "unknown") {
      c.directory.complete = false;
      c.coverage.partial = true;
    }
    if (["unknown", "excluded"].includes(disposition)) {
      o.jar = null;
      o.source = null;
    } else if (disposition === "closed") {
      o.jar.state = "closed";
      o.jar.manifest.status = "closed";
    } else {
      o.jar.state = "undeclared";
      o.jar.manifest = null;
      o.jar.sha256 = null;
      o.jar.blob_sha = null;
      o.source = null;
    }
    assert.equal(m.welcoming(parse(c), now).length, 0);
    assert.equal(m.rankBoard(parse(c), "month", now).people[0].points, 1);
  }
});
test("UTC month/rolling/all-time periods, equal ranks and reconciliation", () => {
  const b = fixture();
  const t = b.tips[0];
  b.tips.push({
    ...t,
    pull_request_id: 202,
    number: 8,
    url: t.url.replace("/7", "/8"),
    author_id: 302,
    author_login: "fictional-second",
    merged_at: "2026-10-31T23:59:59Z",
  });
  let r = m.rankBoard(parse(b), "month", now);
  assert.equal(r.people.length, 1);
  r = m.rankBoard(parse(b), "30days", now);
  assert.deepEqual(
    r.people.map((x) => [x.author_id, x.rank, x.points]),
    [
      [301, 1, 1],
      [302, 1, 1],
    ],
  );
  assert.equal(r.projects[0].tips, 2);
  assert.equal(
    r.people.reduce((n, x) => n + x.points, 0),
    r.projects.reduce((n, x) => n + x.tips, 0),
  );
  assert.equal(m.rankBoard(parse(b), "all", now).people.length, 2);
  assert.throws(() => m.rankBoard(parse(b), "invalid", now));
});
test("milestones and newcomers are recomputed after withdrawals", () => {
  const b = fixture(),
    t = b.tips[0];
  for (let i = 1; i < 5; i++)
    b.tips.push({
      ...t,
      pull_request_id: 201 + i,
      number: 7 + i,
      url: t.url.replace("/7", "/" + (7 + i)),
    });
  assert.deepEqual(
    m.rankBoard(parse(b), "all", now).people[0].milestones,
    [1, 5],
  );
  b.tips.pop();
  const p = m.rankBoard(parse(b), "all", now).people[0];
  assert.deepEqual(p.milestones, [1]);
  assert.equal(p.newcomer, true);
  b.tips = [];
  assert.equal(m.rankBoard(parse(b), "all", now).people.length, 0);
});
test("expired rankings are hidden; re-evaluation never retains old totals", () => {
  const b = parse(fixture());
  assert.equal(
    m.rankBoard(b, "all", new Date("2026-11-05T12:00:00Z")).people.length,
    0,
  );
});
test("welcome rotation is deterministic per UTC day and independent of score", () => {
  const b = parse(fixture());
  assert.deepEqual(
    m.explore(b, now),
    m.explore(b, new Date("2026-11-03T23:00:00Z")),
  );
  assert.equal(m.explore(b, now).length, 1);
});
test("trailing control characters cannot pass identity or timestamp regexes", () => {
  for (const fn of [
    (b) => (b.source_commit += "\n"),
    (b) => (b.repositories[0].repository += "\n"),
    (b) => (b.tips[0].author_login += "\n"),
    (b) => (b.generated_at += "\n"),
    (b) => (b.tips[0].submission_url += "\n"),
  ])
    assert.throws(() => parse(change(fn)));
});
test("merge during collection may follow consent but must precede PR read", () => {
  const b = change((b) => {
    b.tips[0].checks.consent = "2026-11-03T11:00:00Z";
    b.tips[0].verified_at = "2026-11-03T11:00:00Z";
    b.tips[0].merged_at = "2026-11-03T11:30:00Z";
    b.expires_at = "2026-11-05T11:00:00Z";
  });
  assert.ok(parse(b));
  b.tips[0].merged_at = "2026-11-03T12:00:00.000001Z";
  assert.throws(() => parse(b));
});
test("coverage flags agree with observations and diagnostic aggregates", () => {
  for (const fn of [
    (b) => (b.coverage.unknown_tips = 1),
    (b) => (b.coverage.partial = true),
    (b) => {
      b.directory.complete = false;
    },
    (b) => {
      b.directory.search_failed = true;
      b.coverage.partial = true;
    },
    (b) => {
      const o = b.directory.observations[0];
      o.disposition = "unknown";
      o.jar = null;
      o.source = null;
    },
  ])
    assert.throws(() => parse(change(fn)));
});
test("canonical reader UTC offset timestamps remain supported inside jar reports", () => {
  assert.ok(
    parse(
      change(
        (b) =>
          (b.directory.observations[0].jar.fetched_at =
            "2026-11-03T12:00:00+00:00"),
      ),
    ),
  );
});
test("calendar year zero and whitespace-only canonical reader metadata fail", () => {
  for (const fn of [
    (b) => (b.directory.observations[0].jar.default_branch = " "),
    (b) => (b.directory.observations[0].jar.notice = " "),
    (b) => (b.repositories[0].verified_at = "0000-01-01T00:00:00Z"),
  ])
    assert.throws(() => parse(change(fn)));
});
test("integer tokens reject decimal and exponent spellings before JSON.parse", () => {
  const raw = JSON.stringify(fixture());
  for (const token of ["101.0", "1.01e2", "101e0", "101E+0"])
    assert.throws(() =>
      parse(raw.replace('"repository_id":101', '"repository_id":' + token)),
    );
  const b = fixture();
  b.directory.observations[0].jar.manifest.wanted = [
    "101.0 and 1.01e2 are literal text",
  ];
  assert.ok(parse(b));
});
