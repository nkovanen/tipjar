# Welcoming Jar Suggestions Implementation Plan

> **For agentic workers:** Use `executing-plans` inline after parent-owned Terra design approval; no new workers or publication.

**Goal:** Offer a public suggestion path without treating a suggestion as verified welcome or authority.
**Architecture:** Static GitHub form and site anchors; human curation reuses the existing jar reader and board collector.
**Tech Stack:** Existing YAML, HTML, Python unittest and Node site checks; no dependencies.
**Spec:** [design](../specs/2026-11-03-welcoming-jar-suggestions-design.md).

## Global constraints

Design approved by parent-owned Terra review; local implementation authorized. No registry/data/schema/runtime change, CLI helper, third-party contact or real participant fixtures.
Fixed controller `nkovanen/tipjar`; form `suggest-jar.yml`; same-tab static links named `Suggest a welcoming jar`.
Parent owns review, activation and publication; no push/deploy follows from local verification.

## Review focus

Non-owner suggestions grant nothing; hostile links stay inert; manifest precedence remains canonical; no private identity retention; links survive expiry and JavaScript loss.

### Task 1 — one coherent suggestion path (after approval)

**Files:** create `.github/ISSUE_TEMPLATE/suggest-jar.yml`; modify `web/index.html`, `web/leaderboard.html`, `docs/leaderboard.md`, `tests/test_public_board_integration.py`, `tests/web/leaderboard.browser.cjs` (real navigation/accessibility checks); existing Node model tests run unchanged.
**Interfaces:** consume existing `tipjar jar owner/repo` and registry1 `{repository_id, repository}` candidates; produce no new API, schema or collector behavior.
- [x] Add focused assertions for the exact fixed form destination, both static anchor labels/locations and public/non-owner/no-authority/privacy copy; confirm they fail before adding form/links.
- [x] Add the form, anchors and adjacent exact copy from the spec; document the curator procedure and distinct retraction/opt-out treatment.
- [x] Run focused Python/Node tests and inspect desktop/390px keyboard and JavaScript-disabled views against the acceptance matrix; use existing fictional board fixtures only.
- [x] Confirm existing collector tests exercise README candidates and closed-manifest precedence; add a fictional regression only if coverage is missing, without changing the collector.
- [x] Run `python3 -m unittest discover -v`, `node --test tests/web/landing.test.cjs tests/web/leaderboard.test.cjs` and `git diff --check`; record actual failures/skips outside the repo.
- [x] Review changed-file scope, exact links, issue permissions language and privacy retention; send final local SHA for parent-owned independent review before activation/publication.

No package changes are planned; if implementation requires one, stop and revise the scope and packaging verification first.
