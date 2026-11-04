# Tipjar site

The root landing page introduces Tipjar. `leaderboard.html` joins people giving
back, most tipped projects and currently welcoming jars. `directory.html`
preserves the local-first snapshot directory and invitation editor. Tips are
agent work, not money. The six local directory demo projects are fictional samples: no real invitations,
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
This importer accepts format `find-jars-report/1` or `/2`, at most 1 MiB and 200
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

Open `directory.html#maintainers` to prepare an invitation locally. The primary
path generates the exact repository-scoped README snippet: paste it at byte zero
of root README.md, including the blank third line. The initially collapsed
“Optional: detailed preferences or closed status” editor provides `.tipjar.json`.
Its generic wanted/boundary presets are editable examples, not a maintainer
request or approval: replace them with project-specific work and rules, and
review every line. A closed manifest expresses refusal. JSON takes precedence
over README, including invalid, unreadable or unsupported JSON; removing JSON
requires deliberately retaining or removing the README invitation too.

Review the chosen file against project policies, add it through your usual
review process, and deliberately publish it on the default branch yourself.
Copy/download changes no repository, verifies no ownership, and enrolls nobody.
If your browser renames the download, retain the exact root filename `.tipjar.json`.
Use the [current maintainer guide](../docs/maintainers.md#check-the-published-invitation-with-a-fresh-read)
to check the published invitation; indexing can lag or omit projects. The optional
[existing suggestion form](https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml)
is a separate human submission for curator review, never registration.
A welcome supplies no issue approval or execution/publication authority.

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
It accepts the frozen manifest-only `tipjar-board/1` contract and explicit
`tipjar-board/2` invitation observations. Board2 preserves pinned manifest,
README or absent provenance from the canonical invitation2 reader; only a complete
welcome supplies work actions. Plain README and absent observations do not.
Imported local snapshots never become scores.

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
and deployment. The controller owns activation and publication. The collector and predeploy checker
are source-only tools, included with their schemas and disabled workflow examples
in the source distribution; they are absent from installed wheels. The board's
source header links to `nkovanen/tipjar`; its status reports generation, expiry and
the source commit. These are untrusted observations, not proof of achievements,
maintainer endorsement or execution/publication authority. An empty public board
is expected until reviewed opt-ins exist; local demo/import data never fills it.

Clipboard copy uses the browser's secure-context API; if unavailable, it selects
the command for manual copying. Browsers may prompt before downloading JSON.

## Share a repository or contributor view

Open an entity from a board row or welcoming jar, then choose **Copy view link**.
Links stay on the board and pin one numeric identity plus a period, for example
`leaderboard.html?repository_id=101&period=month` or
`leaderboard.html?author_id=301&period=all`. These IDs are fictional examples;
they do not assert real participation. Current names and GitHub URLs come only
from the fetched, validated public snapshot. Unknown or removed IDs show a
generic unavailable message while the global board remains usable.

Repository views show accepted tips for the selected period separately from the
current invitation. A welcome-only repository can have no accepted tips in that
period. Contributor views link to their represented projects; historical receiving
projects are not automatically current welcomes. Month and rolling 30-day views
follow the visitor's current UTC time. A link does not freeze a date, rank or
historical snapshot. The same period controls are available inside each view.

Opening/switching views adds browser history; Back/Forward replays it without
another fetch. Period changes replace the current history entry. Close/Escape
clears the current entry's target and preserves the period; a direct arrival
stays on the board. Modified clicks and new tabs retain normal link behavior.
If clipboard access fails, a read-only link is selected for manual copying.
Expiry closes and clears entity details, scores, copy and current welcome actions.

Invalid, duplicate or conflicting selectors are inert and never become HTML,
commands, identities or requests. Imported local files cannot supply these views.
The root badge's existing `?repo=owner/name` destination, onboarding and no-fetch
CSP remain unchanged. Its explicit board lookup handoff is described below.

## From a README badge to the public board

A valid badge name on the root page offers **Look for this project on the public
board** alongside the existing local invitation editor. The root fetches no data.
The link opens `leaderboard.html?repo=owner%2Frepo&period=month`, a lookup hint
rather than a canonical profile URL. The board uses its one existing snapshot
request and requires an exact, unique current repository-name match. It does not
redirect automatically: choose **Open current project view** to enter the numeric
view. Copy view link remains numeric, and existing invitation checks still apply.

A match establishes only the current snapshot's namespace observation. A renamed
repository's former name is not followed; a reused name might now identify a
different numeric repository. Badge origin and earlier ownership are not verified.
A badge/query match never grants contribution approval or execution/publication
authority. Current accepting projects, closed jars and welcome-only projects can
all have a profile without being equivalent invitations.

A fresh name with no included row shows limited-coverage information and local
onboarding plus the fixed **Suggest a jar for review** form. Missing, malformed,
expired or ambiguous data instead makes lookup unavailable. It supplies no stale
identity or numeric profile link. Suggestions require curator review and never
guarantee listing. No name/body/identity from the URL is added to the external
suggestion form URL.

Name and numeric selectors cannot be mixed or duplicated. Names, periods, encoded
URLs and both query bounds are checked before creating personalized links. Invalid
links use generic copy, never a raw query echo. A name-handoff period change
replaces the current hint entry; Back/Forward recomputes names from the same fresh
snapshot without another request. Changing to a numeric view clears the lookup
panel; close uses the existing global-heading focus fallback when that opener is
removed. Expiry clears matched labels and profile links, including on tab resume.

Without JavaScript, static board, local onboarding and suggestion links remain,
with an explanation that project lookup needs JavaScript and a fresh snapshot.
No browser GitHub API request, new collector/data format or badge protocol is used.

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

README onboarding in `directory.html` validates owner/repo locally and generates
the exact official prefix. The landing `?repo=` parameter only pre-fills that
editor through a locally validated link. No save, clipboard write or GitHub call
occurs on page load. Optional JSON preferences take precedence. Local imports
accept explicit find-jars-report/1 (manifest only) and /2 (versioned invitation
provenance); both remain untrusted observations. The public board retains its
separate, frozen manifest-only board1 contract.

The browser runner also checks direct share URLs, native entity links, clipboard
success/fallback and delayed failure, Back/Forward, selected-period summaries,
modal/heading/opener focus, stale/hostile selectors, welcome-only repositories
and expiry while a shared view is open or a tab resumes. Share screenshots can
be directed to `/tmp/tipjar-share-browser` with `TIPJAR_BROWSER_EVIDENCE`.
