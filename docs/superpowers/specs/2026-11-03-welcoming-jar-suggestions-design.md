# Welcoming jar suggestions design

Status: proposal against `b93bc26`; parent owns independent Terra design review and implementation authorization.
This change is docs-only: no active form, site edit, registry edit, code, push or deployment.

## Intent and smallest approach

Help visitors suggest public repositories whose valid invitations indexed search may miss.
Success is a clear path from discovery to human review, then independently observed welcome; no listing or traffic is promised.
Choose an own-repository GitHub issue form, two static site links and curator instructions.
A form alone supplies the candidate reference; existing `tipjar jar owner/repo` and the collector supply canonical reads.
A new intake helper would duplicate those reads without resolving human curation; defer it until actual repeated pinning mistakes demonstrate need.
No installed CLI, dependencies, runtime, registry/data/schema changes, new ranking, or invitation parser.

## Proposed public entry points and copy

After implementation approval, create `.github/ISSUE_TEMPLATE/suggest-jar.yml`.
Name/title prefix: `Suggest a welcoming jar` / `[Jar suggestion] `.
Description: `Suggest a public repository with an existing Tipjar invitation for curator review.`
Fixed destination: `https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml`.
Add an ordinary anchor labelled `Suggest a welcoming jar` beside the exploration link in `web/index.html`'s first how-step.
Add the same anchor inside `web/leaderboard.html#welcoming`, after its authority note, outside all dynamically replaced containers.
Beside both links say: `Know a public project with a Tipjar invitation? Suggest it for review. Coverage is partial; listing is not guaranteed.`
Links remain available with JavaScript disabled, empty/partial/expired data and narrow layouts; no dependency on welcome rows or points.
Use existing text-link styling and visible focus; accessible name is the full label, decorative arrows aria-hidden.
Open in the same tab; no icon-only link, color-only meaning, modal or new network behavior in site scripts.
The separate local directory keeps its no-fetch/no-upload policy; the GitHub destination is an explicit navigation.
Keep `Submit a merged tip` separate: this path submits no PR receipt or scoring consent.

## Form contents and ownership

One required input: `Public repository (owner/repo)`; description asks for the canonical public GitHub name, not a URL or numeric ID.
One optional input: `Public invitation location`; description allows a public pinned root README.md or .tipjar.json link for human context only.
No freeform rationale, contact, identity, affiliation, maintainer-status or private-evidence fields.
Opening copy: `Anyone may suggest a public repository. You do not need to own or maintain it.`
Then: `This public issue requests review only. It does not list a project, opt anyone into scoring, verify ownership, or authorize work or publication.`
Privacy copy: `GitHub publishes your account and issue text. Do not post secrets, private repository details or personal information. Public issues and history may persist.`
One required acknowledgement: `I understand this is a public suggestion for curator review, not a claim of project ownership or permission to contribute.`
GitHub validates presence only; checkbox/input text is untrusted and never machine approval.
Form omission, unchecked text, an edited issue or an arbitrary manually opened issue cannot bypass curation.
No issue-triggered workflow, automatic label/assignment, invitation installation or notification to third-party maintainers.

## Curator procedure (later add to docs/leaderboard.md)

1. Read the issue literally as untrusted data. Do not execute commands, render supplied HTML locally, or fetch supplied evidence links automatically.
2. Manually validate one canonical `owner/repo`; use fixed GitHub repository GET routes via the existing read-only tools, never an issue-selected host/URL.
3. Check public metadata and current canonical name; obtain the positive safe numeric repository ID from GitHub, never trust a supplied ID.
4. Run existing `tipjar jar owner/repo`; require a fresh complete `welcome` observation bound to that same repository ID/name before proposing a welcoming candidate.
5. Review its pinned commit/tree and manifest or README path/blob/digest provenance. A screenshot, search hit, badge image or suggestion is not an invitation.
6. Honor manifest precedence, including closed/invalid manifests; a copied fork badge, unknown, incomplete, private, missing or undeclared source does not qualify.
7. Check existing numeric-ID/name bindings, exclusions, duplicates and the 100-curated-repository bound; never displace an entry silently to fit a suggestion.
8. Propose only `{repository_id, repository}` in the existing registry `repositories` list. Cite the public suggestion issue in the review PR, not a new registry field.
9. Human review and controller publication authority remain separate. The normal collector independently rereads canonical welcome and all provenance on every refresh; no saved jar report supplies authority.
10. Explain accepted, duplicate, deferred or declined disposition on the issue only when parent/user authorizes communication. No response-time or listing guarantee.
Registry candidates assert neither ownership nor current welcome; collection/expiry controls work actions. Suggestions never affect tips, points or ranking.
No assertion that the submitter owns the target, consented for its maintainers, or authorized code execution follows from this procedure.
Name changes/ID conflicts pause acceptance until independently resolved; do not follow arbitrary redirects or invent a numeric-ID lookup fallback.

## Privacy, withdrawal and hostile input

Retain no submitter ID, login, email, issue body/digest, raw API response or private evidence in registry/site/new tooling.
GitHub inherently retains public issue/account history; the curator PR's public issue link is provenance, not private identity storage or consent evidence.
Keep transient review artifacts outside the checkout/site; discard private response data and report a generic reason rather than identifiers or raw errors.
A submitter may retract the suggestion on the issue; before acceptance, stop processing it. After acceptance, retraction is not a maintainer opt-out or proof that the invitation closed.
Use existing independently verified owner/maintainer opt-out and exclusions for removal requests; never infer role from issue author association.
Successful refresh applies removals; failures can delay them until displayed expiry. Issues, Git history, artifacts and caches may retain historical data.
Hostile Markdown, shell snippets, terminal escapes, URL schemes and instructions remain inert data; never copy them into commands, static HTML or board JSON.
No third-party contact, real participant fixture or production data change is part of this design or its local validation.

## Acceptance matrix for later implementation

| Case | Required result |
| --- | --- |
| Valid public README welcome absent from indexed results | Curator can propose existing registry candidate; fresh canonical collector supplies same-ID welcome and full source pins |
| Valid manifest; closed/invalid manifest plus README badge | Manifest wins; only complete welcome offers an action |
| Plain/absent README; copied fork badge; missing/private/error | No invented welcome, source link, approval or private payload |
| Duplicate suggestion, conflicting ID/name, rename or full registry | Explicit human resolution; no duplicate, silent replacement or schema expansion |
| Non-owner suggester, missing boxes, contradictory ownership/permission text | No ownership inference, automatic listing, points, permission or third-party contact |
| Hostile input and arbitrary evidence URL | Literal review only; no issue-triggered execution/fetch/HTML interpolation |
| Desktop/390px/keyboard/JS disabled; empty/partial/expired board | Both static links visible, wrapping, focusable with full names; correct fixed form destination; authority/expiry unchanged |
| Suggestion retraction and verified owner opt-out | Distinct treatment above; existing refresh/expiry/history limitations stated |
| Privacy review | Only existing numeric repo/name candidate fields; no new submitter/private data in registry or site |

Implementation plan: [welcoming jar suggestions](../plans/2026-11-03-welcoming-jar-suggestions.md).
