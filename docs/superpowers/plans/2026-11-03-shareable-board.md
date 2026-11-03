# Shareable board implementation plan

Status: docs only; parent review/approval precedes product code. Base `57e06bff63bde1fd1cdddd14f0d3f2a272d2e107`; preserve the existing UI branch. No new workers, pushes, workflow activation, deployments or live participants in this task.
Spec: [Shareable board views](../specs/2026-11-03-shareable-board-design.md). Parent owns independent Terra design/implementation review and publication.
Use executing-plans and focused red → green tests after approval. Existing board1/2 contracts, validated data boundaries, scorer and registry are unchanged.

## Files and interfaces

Modify `web/leaderboard-model.js` for pure routing/lookup helpers; `web/leaderboard.js` for view rendering, history and clipboard wiring; `web/leaderboard.html` for the generic share status and focusable board heading. Add minimal `web/style.css` rules only if existing controls cannot fit at 390px.
Extend `tests/web/leaderboard.test.cjs` and `tests/web/leaderboard.browser.cjs`; existing `tests/test_web_leaderboard.py` already runs the Node model suite. Update `web/README.md` with examples after behavior is verified. Do not modify root badge handling, local import helpers, collector, schemas or production data.

- `parseBoardRoute(search) -> {period, target, invalid}`: period `month|30days|all`; target null or `{kind:'repository'|'author', id:<safe integer>}`. Default `{period:'month',target:null,invalid:false}`; bad recognized routing returns that state with `invalid:true`. Bounds and decoding are defined in the spec.
- `boardViewURL(locationHref, route) -> string`: derive same-origin/subpath `leaderboard.html`; emit only validated target and explicit period, no hash/unrecognized query. Internal callers supply normalized routes; reject malformed route objects rather than interpolate them.
- `resolveBoardTarget(board, target, now) -> null | {kind,id,label}`: require fresh validated board1/2 and current included identity; repository label from repo row, author label from whole included tip set. It creates no participant or invitation.
- One `syncBoardRoute({focus})` UI path parses the current URL, synchronizes both period controls, renders the global board and opens/updates/closes the resolved dialog without history writes. The null target remains a normal board; invalid/unresolved targets use only generic status.
- Open/switch, period and close handlers write history as specified, then call the synchronizer. History/state never supplies identity data. Entity renderers reuse existing `repoDetail`, `proofs`, `rankBoard`, `sourceURL` and freshness guards; contributor rendering becomes a named function shared by row and route entrypoints.

## Task 1 — bounded routes and current identity lookup

- [ ] Add failing tests `share_route_rejects_ambiguous_or_hostile_selectors`: both kinds, repeated same/mixed values, empty/zero/leading-zero/negative/float/exponent/unsafe IDs, malformed/double encoding, invalid/duplicate period, >2,048 units and >16 pairs. Assert inert month board, no raw query reflection.
- [ ] Add `share_url_is_canonical_and_subpath_safe`: same-origin `/tipjar/leaderboard.html`, all three periods, one numeric target, ignored query/hash stripped, native encoded digits canonicalized and malformed internal route objects rejected.
- [ ] Add `share_lookup_uses_current_snapshot_only` across archived board1 and shared board2 fixtures: repository welcome-only/no-period-tips, represented author outside period, canonical rename/login, unknown/removed IDs, private/omitted absence, expired board. Assert no synthetic identity and board input unchanged.
- [ ] Run `node tests/web/leaderboard.test.cjs`; new cases must fail for missing behavior while existing parsing/ranking/corpus checks still pass.
- [ ] Implement the three pure helpers only. Re-run that command; expect all cases green. Commit the independently testable routing/lookup boundary.

## Task 2 — linkable views and accessible history

- [ ] Add browser failures for direct repository/author URLs, row/card canonical anchors, new-tab hrefs, current-period summaries/proofs, contributor → represented project navigation and Copy view link exact value/fallback.
- [ ] Add browser failures for Back closes / Forward reopens, target switching, period replace (URL + both controls + visible proofs), close/Escape clears selector without leaving a direct arrival, and direct-load vs connected-opener focus return. Assert no history writes while replaying popstate and no extra board/API requests.
- [ ] Add browser failures for welcome-only/no-period-tips, stale author/repo IDs, hostile/duplicate selectors inert, expired snapshot on arrival and expiry while dialog open or tab resumed. Assert no query-derived links/commands, stale copy or welcome action; preserve board global operation and existing partial/unavailable states.
- [ ] Implement history/synchronizer, named contributor renderer, period controls, canonical anchors and Copy view link. Keep invitation and historical acceptance separate; retain literal text APIs, README/manifest source links and no absent-source file link. Add only needed accessible markup/styles.
- [ ] At desktop and 390px, run `TIPJAR_PLAYWRIGHT=/path/to/existing/playwright TIPJAR_BROWSER_EVIDENCE=/tmp/tipjar-share-browser node tests/web/leaderboard.browser.cjs`; expect all checks green with screenshots for repo, contributor, welcome-only, stale and expired states. Inspect actual renders; report OS clipboard limits honestly.
- [ ] Run `node tests/web/leaderboard.test.cjs`, `python3 -m unittest discover -v` with required locked `TIPJAR_PARITY_AJV`, and `git diff --check`; expect zero failures and no skipped required parity. Packaging checks only if packaging files change (outside this slice).
- [ ] Document current-time period semantics, canonical URL examples, stale-ID behavior and deferred badge-name bridge in `web/README.md`. Commit the verified UI change; report exact head, commands/results and outside-repo screenshot paths for parent-owned independent review. No routine rerun after disjoint docs.

## Review focus and fallback

Check that display identity always comes from the current validated snapshot; duplicate/unsafe selectors cannot influence links, fetches, permissions or scoring. Compare accepted-tip sets/counts to existing rankBoard across periods and both versions.
Check that invitation freshness is independent of selected period and historical merges; no current action for closed/unknown/plain README/absent sources, omitted/private or expired state.
Check popstate/programmatic-close loops, direct-arrival close, disconnected-opener focus, period-control focus and modified-link clicks. Verify root badge onboarding/CSP and local snapshot imports remain unchanged.
If the routing layer cannot resolve a current entity, retain the global board and generic status; do not add fallback data, APIs or name inference. Parent decides any scope expansion after review.
Self-review: each spec boundary maps to the task tests above; three helper signatures and history/period rules are fixed, no new data authority or additional subsystem. Design questions were waived; choices remain subject to parent review.
