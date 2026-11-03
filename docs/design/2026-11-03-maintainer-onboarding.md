# Maintainer invitation onboarding: spec and implementation plan

Status: proposal for parent design review; no implementation or publication.
Base: `d99751abc9f66c618a95e4975630377cc3c9e675`.
Goal: help a first-time maintainer prepare one deliberate invitation for useful
agent work, review it, and understand where to publish and check it.

## Decision and scope

Choose a minimal reorganization of `directory.html#maintainers`. A dedicated
page would give a cleaner title but duplicate routing/editor setup and split
existing links. Keep this stable anchor, clarify the page title and navigation,
and make the anchored panel a self-contained sequence. No new page or wizard.

Use “Local tools & maintainer invitations — Tipjar” as the document title,
“Local demo & imports” for the directory navigation link, and “For maintainers”
for the existing anchor. Retain “Community board” for public observations.
The panel heading remains “Put out your jar”; add “Prepare locally. Review and
publish yourself.” An anchor arrival exposes the heading and first input;
it must not require browsing demo cards to understand or use the editor.
Keep “FICTIONAL DEMO” and the six fictional projects explicitly labeled as
samples, never real invitations, endorsements or evidence of participation.

## Visitor sequence and copy contract

1. **Choose your repository.** Keep the existing owner/repo input and locally
   validated `?repo=` prefill; neither establishes ownership or maintainer role.
   Use a fictional placeholder only. No clipboard write, download or request
   occurs on load, prefill, editing, or opening optional preferences.
2. **Simple welcome: README.** Show the existing snippet preview and explicit
   “Copy README invitation” first. Paste its exact three-line prefix at byte
   zero of root `README.md`, including the blank third line. Keep the project
   title after that blank line; use JSON if the title must stay first.
   Preserve copied-fork correction/removal guidance and manual copy fallback.
3. **Optional: detailed preferences or closed status.** Put the existing
   manifest editor inside a native, initially collapsed `details` with this
   summary. Opening it is optional; README alone does not require JSON.
   Keep both forms and their IDs, validation messages, previews and handlers.
   Once opened, the manifest preview may remain open within this disclosure.
   Label wanted/boundary presets “Editable examples — replace with your actual
   wanted work and contribution rules; review every line before publishing.”
   Generic documentation/tests/ask-first examples are not a maintainer request,
   approval, or an attestation of policy review. No acknowledgment checkbox or
   invented consent gate: deliberate human review is explained, not certified.
   Keep welcome/closed status and “Download .tipjar.json”; download stays local.
4. **Review and publish deliberately.** Place these instructions after both
   paths, outside the optional disclosure, so the simple path has a clear end:
   review the exact snippet or downloaded JSON against project policies; add
   the chosen file yourself through your repository's normal review process,
   then deliberately publish it on the default branch. Copy/download changes
   no repository and this page does not publish, enroll, or verify membership.
5. **After publishing.** Link “Check your published invitation” to the current
   [maintainer guide](../maintainers.md#check-the-published-invitation-with-a-fresh-read).
   In product HTML use `https://github.com/nkovanen/tipjar/blob/main/docs/maintainers.md`
   with that anchor. The guide owns `tipjar jar owner/repo` and bounded
   `find` instructions; indexing can lag or omit projects, with no listing promise.
   An optional “Suggest a jar for review” link uses only the fixed
   [existing suggestion form](https://github.com/nkovanen/tipjar/issues/new?template=suggest-jar.yml).
   It is a separate human submission for curator review, never registration.

Keep precedence visible outside the disclosure: root `.tipjar.json` overrides
README at the same commit, including closed, invalid, unreadable or unsupported
JSON; README cannot rescue it. Removing JSON requires deliberately retaining or
removing the README invitation. Closed status expresses refusal; missing data
never becomes permission. Keep the closed-manifest path easy to discover in
the summary. Welcome grants neither issue approval nor execution/publication
authority; actual project rules and separate human authorization still apply.

## Existing interfaces and invariants

Reuse `TipjarModel.makeBadge(repository)` and `makeManifest(status, wanted,
boundaries)`, `updateBadge()`, `updateManifest()`, and existing copy/download
handlers. Preserve exact generated snippet bytes and parser contracts, JSON
schema/limits/refusals, safe text rendering, and `connect-src 'none'`. No fetch,
GitHub browser API, storage, upload, ownership check or automatic action.
Local imports keep explicit /1 and /2 support, atomic invalid-import refusal,
provenance/trust labels and memory-only lifetime; they never populate scores.
Do not change the canonical generator/parser or add a parallel implementation.
The separately owned badge-name-to-board handoff stays at its existing root
`?repo=`/board interface; do not add lookup logic, fetches or duplicate helpers.
No registry, CLI, schema, scoring, backend, Skill or authorization changes.

## Implementation plan after parent review

- [ ] In `tests/web/browser.test.js`, add focused failing checks for initially
  collapsed optional preferences, visible README/publish/precedence guidance,
  explicit example labeling, guide/form targets, and no automatic side effects.
  Extend existing exact-byte copy, invalid-input, download and import checks;
  opening/closing the disclosure must preserve edited values and validation.
- [ ] Reorganize `web/directory.html` as above; minimally adjust `web/style.css`
  for the standalone panel sequence and 390px layout. Keep stable anchors/IDs.
  Change `web/app.js` only if event wiring needs adjustment; reuse its handlers.
  Leave `web/model.js` unchanged; do not create or edit handoff-owned
  `sharedmodel.js` helpers unless necessary and coordinated with their owner.
- [ ] Update `web/README.md` to describe the two paths and manual publication.
  Run `node tests/web/model.test.cjs` and `python -m unittest discover -v`.
  Serve the existing `tests/web/browser.html` harness; require its completion
  marker and inspect any LIMIT results rather than claiming OS boundaries pass.
- [ ] Verify desktop/390px direct anchor arrival, heading/input visibility,
  keyboard order, native disclosure focus, retained values, readable overflow,
  exact copied bytes/manual fallback, and downloaded closed/welcome manifests.
  Recheck fictional demo/import/reset and hostile-input cases without live reads.
  Verify relative navigation under a project subpath and unchanged no-fetch CSP.
  Record actual checks outside Git; parent reviews the result before publication.

## Design-only acceptance

This change contains only this combined specification/plan (at most 120 lines).
Check local Markdown targets/guide anchor, the fixed suggestion URL against the
existing interface, line count and `git diff --check`; runtime tests are not
needed for this docs-only proposal. Parent owns review, implementation dispatch,
push/PR/deployment and any participant reads or third-party contact separately.
