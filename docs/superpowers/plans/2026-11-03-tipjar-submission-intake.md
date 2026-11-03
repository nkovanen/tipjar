# Tipjar Submission Intake Implementation Plan

> **For agentic workers:** Use `executing-plans` inline; parent owns independent Terra review. No new workers or publication.

**Goal:** Save exact public submission pins/body for human curator review without enrollment authority.
**Architecture:** Source-only intake wraps the existing budget client with an exact seven-route guard and reuses receipt/board eligibility checks. CLI validates a symlink-free destination before reads and exclusively creates a private bounded JSON file after successful observations.
**Tech Stack:** Python 3.10+ stdlib and existing `agent_contribute` resources; fake GET tests, locked development Ajv.
**Spec:** `docs/superpowers/specs/2026-11-03-tipjar-submission-intake-design.md` at reviewed `7a44cf8`.

## Global constraints

- Fixed controller `nkovanen/tipjar`, ID `1444643470`; seven uncached gh invocations, inherited redirects still require matching public identities.
- Explicit issue/PR references; no issue-selected routes, declaration inference, registry writes, installed CLI additions or live participant reads.
- `review-required` plus one LF is the entire success stdout. Exact UTF-8 body hash, 256 KiB body / 2 MiB output; mode 0600 and no overwrite.
- Preserve registry1 and board1/2 contracts; parent owns publication and independent review.

## Review focus

- Equal body observations do not establish edit history; saved body remains untrusted.
- Both transport methods enforce the next exact route before invoking gh; helper changes cannot expand the sequence.
- Final private/identity changes prevent any saved candidate or leaked response.
- Parent/destination links, control-character filenames, concurrent output creation and failed writes preserve existing data.
- Candidate and pins lack declaration fields; copying cannot bypass human semantic review.

### Task 1 — intake observations and local output

**Files:** create `tools/tipjar_board_intake.py`, `tests/test_tipjar_board_intake.py`.
**Interfaces:** `intake(submission:int, reference:str, client=None, *, clock=None)->dict`; `IntakeClient(submission, reference, client=None, *, clock=None)` supplies guarded `request`/`request_once`; `main(argv=None)->int` owns bounded destination/save and fixed diagnostics.
- [ ] Write exact-byte/changed-body/private-final/declaration-absence tests, run `python3 -m unittest tests.test_tipjar_board_intake -v`, observe missing intake fail.
- [ ] Implement seven-step observations, strict pins, and fixed five-item review checklist with no declaration fields.
- [ ] Add route guard, identity/merged-fact, malformed/oversized body and failure/no-output matrix; prove new boundary cases fail before fixing.
- [ ] Add CLI destination/control-name/mode/concurrent-create/write-cleanup cases; implement bounded exclusive output with parent checks and fixed stdout.
- [ ] Run focused intake and existing board/receipt tests; expect PASS; commit reviewable helper and tests.

### Task 2 — curator documentation and source packaging

**Files:** modify only curator section of `docs/leaderboard.md`, `MANIFEST.in`, and `tools/check_install.py` source inclusion/wheel exclusion checks.
**Interfaces:** source archive includes helper; installed wheel/CLI remain unchanged; docs instruct review of candidate bytes, manual declaration additions and complete registry validation.
- [ ] Add source inclusion assertion and confirm existing wheel-wide tools exclusion covers intake; include helper in source manifest.
- [ ] Document exact command, review-only output, unchanged human declarations/dedup/withdrawal requirements; no production registry or site changes.
- [ ] Run full `python3 -m unittest discover -v` with required locked Ajv and actual Python 3.10 affected tests; expect PASS.
- [ ] Run clean `python3 tools/check_install.py` build/install checks and inspect output; run `git diff --check`, commit final candidate and send exact SHA for parent-owned Terra review.

Execution authorized by parent after Terra design approval; no additional implementation approval gate in this plan. Evidence stays outside the repository.
