# README badge → current public board handoff

Status: docs-only proposal for parent-owned Terra design review; no product code or publication authorized here.
Exact base: `33bc5ef3aefd663398f751873c803f0aa4a747fc` (shareable views merged). Routine choices below are designer decisions subject to review.

## Product choice

A badge click should explain Tipjar and offer a clear path toward the named project's public observations, without treating a badge URL as an invitation or identity proof.
The canonical badge stays byte-for-byte `https://nkovanen.github.io/tipjar/?repo=owner%2Frepo`, with the existing README prefix/image/link protocol unchanged. The root continues to make no data requests.

| Approach | Benefit | Tradeoff |
| --- | --- | --- |
| Root link → current-snapshot name lookup panel → numeric project link (recommended) | Relevant project traffic; explicit identity/coverage boundary; reuses existing detail | One confirmation click and a small temporary name-route state |
| Keep onboarding and add only a generic board link | Smallest change; no name resolution | Visitors must search manually; historical/non-welcoming receiving projects are harder to find |

Designer choice: use the explicit lookup panel, not an automatic redirect/open. Root offers **Look for this project on the public board** beside its existing local invitation-preparation link. The board resolves the name after its one existing validated snapshot load, then offers **Open current project view** using the existing numeric canonical URL.
No extra GitHub calls, root fetch/CSP weakening, collector changes, board/CLI schemas, scoring, registry changes, Markdown parsing, accounts, cached aliases or real-looking participant examples. Existing numeric links remain canonical; name URLs are only lookup hints.

## Bounded input and navigation contract

Root handoff URL: relative `leaderboard.html?repo=owner%2Frepo&period=month`; use URL/URLSearchParams and the current project-subpath base, never concatenate an unescaped query into a URL. Root may forward a valid explicit `month|30days|all`; omitted period defaults to month.
Before root or board acts on `repo`, enforce the existing 2,048 UTF-16-unit search limit, at most 16 parameter pairs, and exactly one decoded `repo` value. Validate the complete decoded string with the existing ASCII owner/repository grammar (max 39/100 characters); lowercase only after validation. No trimming, extra decoding, partial match or GitHub URL interpretation.
`repo`, `repository_id` and `author_id` are mutually exclusive target selectors. Duplicates (including identical values or encoded key spellings), conflicting kinds, empty/malformed name, and invalid/duplicate period make routing inert. Unknown keys are ignored, not reflected or forwarded. Existing numeric-only routing retains its reviewed behavior.
Malformed/double encoding, raw HTML, controls, path traversal, URL/shell syntax and oversized queries cannot become a link target, command, identity, issue prefill or request. Use generic invalid-link copy, never the raw failing parameter (replace the current landing error's raw echo).
A valid root name remains an explicitly user-supplied onboarding hint, not public repository metadata. It may generate the existing local `directory.html?repo=...#maintainers` link; invalid/conflicting inputs generate neither personalized action. Static site navigation remains available.

## Current identity, freshness and ambiguity

Resolve only against `board.repositories` from the current successfully parsed, unexpired board1/2 snapshot: at most 200 rows, exact full-name equality after ASCII lowercase, exactly one match. Never search partial names, tip text, directory imports, browser storage, old snapshots, API redirects or GitHub itself.
On one match, show **Current public snapshot match**, its validated canonical name, current observation time/expiry and a numeric **Open current project view** anchor built by the existing boardViewURL. A match can be a welcome-only jar, a receiving project whose jar is closed/unknown, or a represented project with no selected-period tips. Current name is metadata, never a welcome claim.
Panel copy: “This matches the name in your link. Badge origin and earlier ownership are not verified.” Only the existing numeric detail evaluates current invitation separately from historical acceptance; no contribution command or welcome badge appears in the lookup panel.
A rename may leave no current name match; do not follow or remember its former name. If a namespace is reused, an exact current match can belong to a different numeric repository than the badge author originally intended. The name-only badge cannot disambiguate this; the confirmation panel makes only a present-name observation. Never assert continuity, original badge ownership or permission. Stable numeric share links survive renames only while their ID remains included.
No match or multiple matches means no profile, inferred ID, canonical GitHub link, score, welcome or numeric share link. Multiple matches are unavailable/ambiguous rather than “not listed”; validators normally reject such snapshots, but lookup must never choose the first.
Fresh no-match copy: “Not listed in this snapshot. Coverage is limited; this does not mean the project has no invitation.” Offer **Prepare an invitation locally**, the generic board/directory navigation, and **Suggest a jar for review** at exactly `https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml`. Do not append query-derived repo/body/identity fields to that fixed external URL. Submission is curator review, not enrollment or approval.
Missing/malformed/expired snapshot means lookup unavailable, not no-match: retain existing overdue/unavailable status and hide matched identity/link. Static onboarding/suggestion links may remain, clearly independent of any verified identity. Never substitute cached matching rows or stale aliases.

## History, periods, focus and fallback

Keep the bounded name hint in the address bar while the lookup panel is shown. Selecting its numeric anchor uses the existing same-page route/history behavior; Back returns to the name lookup and recomputes against the same current snapshot, Forward resolves the numeric view. Copy view link remains numeric only; no Copy-profile action exists on the lookup panel.
A period change while in lookup replaces the current name-handoff URL with the same validated hint and new period, rerenders global rankings and rechecks current freshness without fetching. A numeric detail retains all existing close/Escape, focus and period behavior. Popstate resolves hints anew and writes no history; a missing hint never reuses the previously matched ID.
After direct name arrival, focus a tabindex=-1 lookup heading when data finishes loading; show bounded status before load without echoing the raw query. Clear/remove the lookup panel when switching to a numeric route, so its disconnected opener uses the existing global-heading focus fallback on close. Back recreates the panel through fresh lookup; never retain a hidden matched identity across unrelated routes or unavailable/expired data. Existing connected numeric-row opener behavior stays unchanged. No focus stealing on unrelated global board navigation.
Expiry, including visibility resume, clears matched label/link and any numeric dialog/copy/current-work action under the existing expiry guard. Retain the URL as a hint, but it cannot display prior identity while overdue. The global board stays functional for valid data and keeps its honest empty/partial states.
Use native anchors, literal DOM text and existing cream/ink/orange styling. Unmodified same-page clicks may reuse the existing router; modified clicks/new tabs stay native. No external redirect, title derived from raw input, or arbitrary fetch.
Root and board include static no-JavaScript links to the community board, local onboarding/directory and the fixed suggestion form. Explain that project lookup needs JavaScript and a fresh snapshot; do not claim dynamic identity resolution works without it. Root keeps connect-src 'none', board keeps its existing same-origin snapshot policy.

## Acceptance matrix

| Case | Required result |
| --- | --- |
| Existing canonical badge / numeric share URL | Badge bytes/protocol unchanged; root onboarding preserved; numeric routes unchanged |
| Fresh exact name (mixed case / encoded slash), board1/2, project subpath | One panel match from current rows; canonical numeric anchor; correct period; no extra fetch |
| Current receiving / welcome-only / zero-period / closed or unknown jar | Numeric profile possible; lookup never supplies invitation or points; existing detail separates work/invitation |
| Renamed absent old name / removed or omitted/private row | No alias/ID/profile inference; limited coverage explanation on fresh no-match |
| Reused current name / ambiguous match | Current-only disclaimer and explicit confirmation; ambiguity never selects an ID |
| Unknown valid name / invalid or duplicate/conflicting selectors | Fresh no-match offers fixed review/local flows; invalid routing offers static generic flows only; raw query inert |
| Missing/malformed/expired/late-expiry data | Lookup unavailable, no stale labels/links/copy/CTA; URL retained, existing global status intact |
| Back/Forward, period, Escape, modifiers, no JavaScript, desktop/390px | No history loop or new data request; correct focus; static fallbacks; no overflow |
