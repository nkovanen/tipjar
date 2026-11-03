# Ordinary contribution implementation plan

> After independent Terra design approval, use `executing-plans` inline; no new workers or implementation is authorized by this document.

**Goal:** Make ordinary human-led contribution primary and advanced Tipjar tooling explicitly optional.
**Architecture:** Copy/navigation changes in existing surfaces, plus bounded current-guide corrections; no new runtime protocol.
**Tech Stack:** Existing static HTML, plain JS and Markdown; no dependencies.
**Spec:** [Ordinary contribution design](../specs/2026-11-03-ordinary-contribution-design.md).
**Base:** Design inspected d99751a; execution must use the final integrated badge-handoff head supplied by the parent.

## Global constraints

- Preserve adopted-task restrictions/refusals, project AI rules, maintainer scope and separate user execution/publication authorization.
- Ordinary work is never claimed machine-verified; native issuer absence is explicit; no generated consent records.
- Keep CLI/task/data/schema/gates/Skill, submission eligibility, collector/scoring and publication authority unchanged.
- Preserve ff7's separate badge-name lookup/router sections and the maintainer/suggestion lanes; no opportunistic cleanup.

## Review focus

- New visitors must find ordinary guidance before CLI installation, without interpreting invitation as issue approval.
- Blocked/adopted tasks cannot use ordinary guidance as a bypass, including after a refusal or missing host record.
- Closed/unknown/undeclared/absent/expired states retain no work-start CTA; historical tips never supply a welcome.
- Current output4/invitation2 wording must not reinterpret task0.1/0.2 or rewrite dated schemas/designs/plans.
- Fixed guide links must work under the Pages project subpath and remain separate from badge-handoff routing.

## Task 1: One coherent ordinary-first guide and handoff

**Modify:** `docs/tipping.md`, `docs/getting-started.md`, `web/index.html` step02, `web/leaderboard.js` welcome-only helper.
**Also modify:** only the four identified current output-version sentences in `docs/upgrading.md`, `docs/host-authorization.md`, `docs/architecture.md`, `docs/getting-started.md`.
**Test:** existing `tests/test_docs_consistency.py`, `tests/web/leaderboard.browser.cjs`, `tests/web/landing.test.cjs`; extend only meaningful navigation/state regressions.
**Interface:** consume existing validated fresh-welcome branch and fixed guide URL; produce no new function, command, route, schema or consent field.
- [ ] Read the approved spec and final integrated source; confirm ownership sections with parent, retaining ff7's exact reviewed bytes outside these sections.
- [ ] Add focused regressions for a working ordinary guide anchor/primary link, retained optional install link, and welcome-only guidance without an extra request.
- [ ] Include manifest/README welcomes and closed/unknown/undeclared/absent/expired controls; assert guide copy never describes ordinary work as verified or a bypass.
- [ ] Run `python3 -m unittest tests.test_docs_consistency -v` and the existing Node/browser harness; observe the new navigation expectations fail before product edits.
- [ ] Apply the spec's exact UI copy/link changes; keep the discovery command/clipboard behavior and existing safeguards intact.
- [ ] Add the ordinary introduction and optional advanced labels; explicitly retain adopted-task stops and real human authorization before execution/publication.
- [ ] Apply only the specified tipping drift corrections and four output-version sentences, using actual CLI/schema output and resolver source; retain historical text elsewhere.
- [ ] Add a bounded docs assertion only where it catches meaningful current-version drift; do not snapshot every sentence or duplicate generated schema tests.
- [ ] Rerun focused checks, `node tests/web/leaderboard.test.cjs`, `node tests/web/landing.test.cjs`, and the real browser harness using existing Playwright.
- [ ] Manually inspect ordinary-first order, optional CLI path, external guide anchor, keyboard focus and 390px/desktop layouts; confirm no new work invitation in stop states.
- [ ] Run the full repository suite with locked `TIPJAR_PARITY_AJV`: `python3 -m unittest discover -v`; report real counts, skips and limitations.
- [ ] Diff-check frozen resources and shared UI sections; commit the narrow coherent slice, record exact source SHA and request parent-owned independent review before publication.

## Design-stage evidence

Only this spec and plan are created now; no product edits, tests, workers, push or deployment.
Offline exact-base CLI inspection confirmed version0.3.0, output schema4, task schemas0.1/0.2/0.3 and existing commands; no GitHub reads were needed.
