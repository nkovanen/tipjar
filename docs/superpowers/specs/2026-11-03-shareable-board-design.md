# Shareable Tipjar board views

Status: docs-only proposal for parent-owned independent design review. No product implementation or publication authorized by this document.
Base: `57e06bff63bde1fd1cdddd14f0d3f2a272d2e107` (pending PR #10). Routine choices below are the designer's calls, not new user requirements.

## Intent and approach

Help people share accepted contributions and send visitors toward currently welcoming projects, using only the already fetched and validated board1/2 snapshot.
A repository view joins its accepted tips with a separately labeled current invitation. A contributor view joins that person's accepted tips with the represented projects and existing proof links.

| Approach | Benefit | Cost |
| --- | --- | --- |
| Dedicated repository/contributor pages | More room and potential static social previews | Additional entrypoints, renderers and navigation; rich previews would need a separate publishing design |
| Query-linked existing detail dialog (recommended) | Small change, one loader/validator/freshness boundary, global board stays available | Shared links open a modal; static social cards remain generic |

Designer choice: extend the existing dialog and add **Copy view link**. Preserve warm styling, global rankings, directory tools, CSP, source provenance and keyboard access. No new pages, APIs, fetches, schemas, score rules, enrollment, real-looking demo activity or Markdown parsing. No claim that a tip, badge, score or share link supplies authority.

## URL and resolution contract

Canonical examples: `leaderboard.html?repository_id=101&period=month` and `leaderboard.html?author_id=301&period=all`.
Exactly one optional target: `repository_id` or `author_id`. IDs must decode to canonical ASCII decimal `[1-9][0-9]{0,15}`, without leading zeroes, and be JavaScript safe positive integers. Period is optional `month|30days|all`, default `month` (current UTC calendar month).
Bound the raw search string to 2,048 UTF-16 units and 16 parameter pairs before processing. Unknown keys are ignored and never copied or displayed. Duplicate recognized keys, two target kinds, invalid/empty IDs, or invalid/duplicate period invalidate routing: show the ordinary month board with no target. Never echo raw query text.
Malformed percent escapes, encoded markup, whitespace, negative/float/exponent/unsafe IDs and double-encoded selectors cannot become an identity, URL, command, HTML or new request. Standard one-pass URLSearchParams decoding may accept encoded decimal digits and the builder canonicalizes them.
Resolve a repository only by numeric ID in `board.repositories`; resolve an author only from `board.tips` across the whole included snapshot, not the currently selected period. Use current validated names/logins for headings and construct existing canonical GitHub links from snapshot identities.
A missing/withdrawn/omitted/private/stale ID supplies no inferred name, profile, source link, command or zero-count participant. Show a separate generic status near the board controls: “This shared view is unavailable in the current snapshot.” Keep the global board usable; never replace its freshness/coverage status or expose the queried ID. Retain a syntactically valid unresolved URL so reloading can resolve against a later snapshot.
Never resolve names or IDs through GitHub, a browser token, local imports, stored history/state or a prior snapshot. A renamed entity keeps its numeric link only while represented in the current snapshot.

## Content and period semantics

Every ready view labels the selected period, snapshot generation/expiry and curated/partial/equal-point caveats. Reuse `rankBoard` accepted rows and summaries; do not introduce a second period filter or scorer.
Repository: current canonical repository link, existing language/check metadata; selected-period tips, distinct contributors and accepted-tip proof list; then **Current invitation**, independent of period. Keep current README/manifest pins and the existing welcome-only discovery command. Closed/unknown/absent/undeclared sources never supply a new-work action. No source link for absent.
A represented repository with no selected-period tips, including a welcome-only jar, remains shareable: say “No accepted tips in this period,” without implying no historical work or exhaustive coverage. Its invitation can still be current and welcoming.
Contributor: current snapshot login, selected-period points/distinct projects, accepted PR + opt-in proof links, and unique represented project links ordered by numeric repository ID. A currently represented author with tips only outside the selected period gets an honest zero-period state, not a missing-identity state. A removed author with no included tips is unavailable.
Represented project links open the corresponding repository view; its current invitation is checked separately. Do not imply the contributor's historical receiving projects currently welcome new work. Existing size context remains context, never points.
Designer choice: both dialog and global board expose the existing three period choices; changing either synchronizes both and rerenders the view. Month/rolling periods remain relative to the visitor's current UTC time; shared URLs do not freeze dates, ranks or historical data. Include this short explanation by Copy view link.

## Navigation, sharing and accessibility

Use real same-page anchors with canonical hrefs for contributor/project rows, welcome cards and represented projects; intercept only unmodified primary clicks. Modified clicks/new tabs and browser link copying retain native behavior.
After the one existing snapshot fetch succeeds, resolve the initial query once. Opening/switching a target uses pushState only when the normalized URL changes; selected-period changes use replaceState and preserve the target. Copy view link builds from the current same-origin project-subpath `leaderboard.html`, includes explicit period and exactly one numeric target, and drops unknown keys and fragments.
Close/Escape removes target selectors using replaceState, preserves period and returns focus to the actual opener if connected, otherwise the board heading. It never calls history.back, so a direct arrival cannot unexpectedly leave the site. Explicit close clears the current entry; Back/Forward otherwise replay prior URLs (Back from an opened view closes it, Forward reopens it; switching targets can be traversed).
A single route synchronizer handles initial load, popstate, opening, period change and close. Popstate must not write history or fetch. Suppress route writes during programmatic dialog closes/rerenders/expiry; no close-event loops or duplicate showModal calls.
On direct opening, focus the dialog heading with tabindex=-1; preserve the selected period control's focus during rerenders. Keep the native modal trap, accessible title, Escape and existing close button. If a prior opener disappears during rendering, focus the global board heading with tabindex=-1.
Copy view link uses the existing secure clipboard pattern with selectable-link fallback and role=status feedback; copying executes nothing. Check freshness again immediately before copy or any welcome command action.
Expiry or unavailable/malformed snapshot suppresses all entity content, scores, current welcome/copy actions and closes any dialog, including after visibility resume. Retain the URL without synthesizing cached content. Show existing overdue/unavailable state and the global navigation; a reload may recover from a new snapshot. No extra fetch on history or period changes.

## Badge landing and first-slice fallback

Preserve the existing root `?repo=owner/name` badge destination, canonical badge protocol and safe maintainer-onboarding behavior. The root keeps its no-fetch CSP; existing Community board / Find a jar navigation remains the route to public observations.
Designer choice: defer automatic badge-name → board-entity matching in this slice. It would add another selector/lookup flow; the new share links originate from entities already resolved in the board. A future bridge must resolve a canonical name only against the current validated public snapshot, never infer an ID/permission or weaken root CSP.
If routing/sharing is unavailable (including no JavaScript), ordinary global board navigation and existing CLI/source/onboarding links remain. Unknown/expired data never falls back to fictional or cached entity content. Generic social previews are acceptable; dynamic metadata, analytics and traffic claims are deferred.
