# Badge-to-board handoff implementation plan

Status: docs only, pending parent-owned Terra design approval. Base `33bc5ef3aefd663398f751873c803f0aa4a747fc`; implementation must begin only on later explicit authorization.
Spec: [README badge handoff](../specs/2026-11-03-badge-board-handoff-design.md). Preserve the earlier numeric share-view design and board1/2 contracts. No workers, push, PR, deployment or live participants here.
Fixed concurrent suggestion interface only: `https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml`; do not depend on or modify that worker's form/collector code.

## Files and concrete interfaces

Modify `web/model.js` only to add shared bounded handoff parsing/building, preserving makeBadge output and all local import/editor contracts; `web/landing.js` and minimal `web/index.html` static fallback markup; `web/leaderboard-model.js`, `web/leaderboard.js`, minimal `web/leaderboard.html` panel markup, optional minimal CSS. Extend `tests/web/model.test.cjs`, `tests/web/leaderboard.test.cjs`, `tests/web/leaderboard.browser.cjs`; update `web/README.md`. Collector, CLI, schemas, registry, canonical invitation parser and badge assets are out of scope.
- `TipjarModel.parseRepositoryHandoff(search) -> {repository:null|string, period, invalid}`: bounded root/name parser; reject numeric-selector presence, duplicate/conflicting recognized keys and invalid period/name; return lowercase validated name only. No name means no personalized actions.
- `TipjarModel.repositoryHandoffURL(locationHref, entry) -> string`: same-origin/project-subpath leaderboard URL with exactly encoded `repo` and explicit valid period; reject malformed/invalid entries. This is a lookup URL, not a canonical entity URL.
- Extend `TipjarBoard.parseBoardRoute`'s internal target union with `{kind:'repository-name',name}` only when a unique valid repo selector exists. Numeric-only results remain unchanged; mixed target kinds fail closed. Reuse shared handoff parsing; canonical `boardViewURL` must continue to reject name targets.
- `TipjarBoard.resolveRepositoryName(board, name, now) -> {status:'matched',target:{kind:'repository',id,label}} | {status:'not-listed'|'unavailable'}`: validated fresh board only, exact unique full-name comparison against current rows. Fresh zero matches is not-listed; ambiguity/expiry is unavailable. It creates no alias and evaluates no invitation/scoring.
- Existing `syncBoardRoute` renders a distinct lookup panel for name targets; numeric details still use existing numeric lookup. Matched panel anchors use `boardViewURL` with the resolved numeric ID. Route mutation chooses `repositoryHandoffURL` only to preserve a validated pending name during period changes. No storing a resolved ID in history, local storage or query-derived metadata.

## Task 1 — bounded hints and explicit root handoff (red → green)

- [ ] Add model failures for root duplicate/encoded-key/conflicting selectors, malformed names/encodings/controls, both bounds, invalid periods, ignored extras and canonical encoded subpath URL. Assert no raw echo or personalized links from invalid input; freeze exact makeBadge bytes and existing import/editor cases.
- [ ] Add board model failures for numeric/name dispatch isolation; reject name targets in canonical builder; unique exact mixed-case match across board1/2; fresh absent/removed/omitted name; expired/ambiguous names; rename/reused-name current-only outcomes. Assert no input mutation, alias inference or second scorer.
- [ ] Run `node tests/web/model.test.cjs` and `node tests/web/leaderboard.test.cjs`; confirm new assertions fail for missing behavior. Implement the three pure boundaries and shared route dispatch, then root links/generic invalid state only. Re-run focused suites; expect all green. Commit the independently testable parsing/root handoff.

## Task 2 — snapshot match panel and review fallbacks (red → green)

- [ ] Add browser failures for original root badge URL → explicit board lookup → numeric detail/copy link; fixed no-match suggestion/local flows; matched canonical identity text, no invitation in panel, current receiving/welcome-only/closed/unknown cases, no period tips, both board formats.
- [ ] Add browser failures for renames/no aliases/reused names, malformed/duplicate/conflicting query inert, no arbitrary external URLs, one board.json request, zero root data fetches and zero browser GitHub API requests, preserved root CSP/badge generation/import workflow.
- [ ] Add browser failures for name period replace, Back/Forward name↔numeric replay without extra fetch/history writes, direct-arrival and connected/disconnected-opener focus, native modifiers/new tabs, no-JavaScript static navigation, empty/partial/unavailable/expired/visibility-resume states. Assert expired matched labels and numeric links are cleared.
- [ ] Implement the panel and bounded fallback text/actions using existing router/freshness/literal-text/link helpers. Clear/remove the lookup panel when opening numeric detail so disconnected-opener close focus falls back to the global heading; Back recomputes the panel. Never carry a match across unrelated routes or unavailable/expired state. Re-run model/browser suites; expect green.
- [ ] Inspect actual desktop and 390px renders for root context, match, no-match, stale and numeric detail; save evidence outside repo. Run required-Ajv `python3 -m unittest discover -v`, both Node suites, and `git diff --check` once final code; report exact results/limits. No packaging rerun unless actual package paths change.
- [ ] Document name-hint ambiguity, limited coverage, canonical numeric sharing and fixed suggestion-review flow in web README. Commit reviewable code; parent owns independent implementation review/publication. No routine rerun after disjoint docs.

## Review focus / fallback

Require exact current name match before any profile; no query/old state can grant identity, invitation or authority. Ensure no-match and unavailable/ambiguous are distinct, and numeric routes cannot silently win over conflicting names.
Confirm case-insensitive names are namespace observations, not historic continuity; name reuse cannot prove badge provenance. Check history/popstate/period/focus/expiry and asynchronous clipboard behavior retain the numeric slice's protections.
Fallback is existing global board, local onboarding and the fixed suggestion form, never extra APIs or stale aliases. Parent decides any expansion after review. Self-review: each acceptance matrix row maps to tests above; interfaces and ownership fixed; no product code in this amendment.
