# Tipjar site

The root landing page introduces Tipjar. `leaderboard.html` joins people giving
back, most tipped projects and currently welcoming jars. `directory.html`
preserves the local-first snapshot directory and invitation editor. Tips are
agent work, not money. The six initial projects are fictional samples: no real invitations,
endorsements, contribution counts or claims of maintainer consent.

From a source checkout (or extracted source distribution):

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory web
```

Open http://localhost:8765 for the landing page, or
http://localhost:8765/directory.html for local tools. No frontend installation,
build, credentials, remote fonts, telemetry, or browser GitHub requests are needed.
The local directory does not save imported data; reloading restores its demo. The Python package/wheel is independent of
the site. Node is optional for development: `node tests/web/model.test.cjs` tests
the data boundaries; unittest runs it when Node is available.

## Use a real snapshot

In this unreleased preview, export a bounded public search batch with the candidate CLI:

```sh
tipjar find > jars.json
```

Choose or drop `jars.json` in `directory.html` beneath the local directory. Search coverage is partial and indexing may lag;
no adoption or exhaustive directory is established. A failed/incomplete batch may
still retain observations; inspect its diagnostics before using it.
This importer requires format `find-jars-report/1`, at most 1 MiB and 200
observations. It ignores extra bounded metadata, rejects unknown formats,
invalid identities, conflicting dispositions, duplicate repositories, invalid
UTF-8 and unsupported manifest schemas. Example **fictional** snapshot:

```json
{
  "format": "find-jars-report/1",
  "complete": true,
  "observations": [{
    "repository": "example/project",
    "disposition": "welcome",
    "jar": {
      "repository": "example/project",
      "state": "welcome",
      "complete": true,
      "commit": null,
      "sha256": null,
      "manifest": {"schema_version": "0.1", "status": "welcome", "wanted": ["Documentation"]}
    }
  }]
}
```

A snapshot is untrusted data, not verified permission. The overall `complete`
flag reports whether this bounded batch finished its reads without unresolved
observations/errors. It never means exhaustive discovery: indexed coverage is
always partial, including when `complete` is true. Each jar has its own read
completeness. Search errors appear separately from coverage and batch-read status.
Canonical null repository observations (malformed or privacy-suppressed hits)
are counted as skipped, without inventing names or displaying their identity
metadata. An invalid null diagnostic still rejects the entire import and leaves
the prior collection intact. Search diagnostics are bounded to 200 strings of
at most 500 codepoints; unknown diagnostic text is not displayed.
Incomplete jars cannot be welcomed. Unknown and excluded observations offer only
reinspection; closed declarations stop work. Source URLs are generated from
validated GitHub repository/commit identities; imported URLs are never used.
Use the detail commands to recheck current declarations and policies, then
inspect an issue. Replace `ISSUE_NUMBER` before running the inspect command.
Welcome grants neither issue approval nor local execution/publication authority.

## Maintainer draft

Edit the status, wanted work and boundaries. The preview/download uses the exact
0.1 manifest schema (at most 16 distinct lines per list, 500 characters per line,
16 KiB JSON). Exact line content is preserved; empty lines are skipped, but
whitespace-only lines and control characters are rejected. The 32768 UTF-16-unit
input memory cap exceeds every schema-valid per-field value (at most 16015 units
including line breaks); the schema still counts Unicode codepoints. Review the downloaded `.tipjar.json`, then add it to your repository
yourself. Downloading changes no repository. A closed manifest expresses refusal.

## Public community board

`leaderboard.html` fetches only relative, same-origin `board.json`. Its CSP allows
same-origin connections; the landing and local directory retain `connect-src
'none'`. No browser token or GitHub API call is used. Snapshot loading has a
4 MiB streamed byte cap, fatal UTF-8 decoding, a timeout and redirect refusal.
The parser rejects unknown formats/fields, recursive duplicate keys, identity
conflicts, unsupported invitation sources and inconsistent checks/expiry.
It supports the manifest-only `tipjar-board/1` contract; future reader or board
shapes require explicit review. Imported local snapshots never become scores.

Rankings are derived from the same eligible tip set: one point per merge, tied
ranks, UTC calendar month/rolling 30 days/all time. Proof dialogs link to the
merged PR and public opt-in submission. Welcome details show wanted work,
boundaries, pinned provenance when provided and a copyable discovery command.
Closed/unknown jars have no new-work action. At expiry, both scores and welcome
actions disappear, including any open detail dialog. Missing/invalid snapshots
show an honest unavailable state; there is no production demo fallback.

The Pages artifact is the contents of `web/` plus a freshly generated
`board.json` beside `index.html`; no frontend build is needed. Relative links
preserve project subpaths. Never copy test fixtures into a production artifact.
See [board operations](../docs/leaderboard.md) for collection, opt-in, moderation
and deployment. The controller owns activation and publication.

Clipboard copy uses the browser's secure-context API; if unavailable, it selects
the command for manual copying. Browsers may prompt before downloading JSON.

## Browser checks

Verify desktop and 390px layouts, search/filter/empty states, detail dialog via
keyboard and Escape focus return, closed/unknown/excluded stops, valid/invalid
file input and drop, literal hostile HTML, preview validation and JSON download.
No receipt/impact viewer is included; its contract is a separate feature.

The repeatable DOM-event regression page is `tests/web/browser.html`. For local
QA, serve the repository root with `python3 -m http.server 8766 --bind 127.0.0.1`
and open `http://localhost:8766/tests/web/browser.html`. It exercises actual file
input, synthetic drop events, invalid-import preservation, hostile text, editor
limits, and copy/download boundaries. Clipboard and download OS boundaries are
replaced to inspect exact values; native keyboard actions and the OS clipboard /
save dialog still require manual testing. A background browser may defer the
native close event; the page reports this as a LIMIT rather than a passed check.


Public model regressions: `node tests/web/leaderboard.test.cjs` (also run by
`python3 -m unittest tests.test_web_leaderboard -v`). They cover the closed
contract, source pins, identity joins, UTC periods/ties, milestones, conservative
expiry and removal of actions for closed/unknown/expired jars.

Optional real Chromium checks use an already installed Playwright module:

```sh
TIPJAR_PLAYWRIGHT=/absolute/path/to/playwright node tests/web/leaderboard.browser.cjs
```

This starts a temporary local server and intercepts the board request with
clearly fictional fixtures. It verifies desktop/390px/subpath navigation,
proof URLs, native keyboard/Escape/focus return, hostile text, search, missing and
invalid JSON, empty/partial states, live expiry, closed-jar restrictions and the
existing local import harness's final completion marker. Screenshots and the
local harness report go outside the checkout to `/tmp/tipjar-board-browser`
(or `TIPJAR_BROWSER_EVIDENCE`). Native OS clipboard/save dialogs remain manual
checks; the local harness replaces those boundaries and reports any LIMIT lines.
