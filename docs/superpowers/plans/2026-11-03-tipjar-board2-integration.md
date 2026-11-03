# Tipjar Board2 README Invitation Integration Design and Plan

> **For agentic workers:** After controller design approval, use `executing-plans` task by task. Parent owns fresh Terra design review; no new workers or implementation in this amendment.

**Goal:** A canonical README welcome can appear in the public directory, with pinned provenance and unchanged opt-in scoring.
**Architecture:** Explicit board2 collection consumes canonical invitation2/find2. Version-dispatched Python/JS readers retain frozen board1 support; no board-side badge parser or migration of old observations.
**Tech Stack:** Existing Python stdlib, canonical reader, closed JSON Schemas, plain JS, locked development Ajv.
**Spec:** Design contract below extends the approved board design at `bddf6d658df05f0727088dd966627663e15d0333:docs/superpowers/specs/2026-11-03-tipjar-leaderboard-design.md`; the original eligibility/privacy/time rules remain binding.
**Status:** Docs-only proposal, not implementation/publication authorization. Existing board1 release proceeds independently.

## Inspected source and review gate

Reader checkpoint is immutable `85f51abcd3aaba27a4a6cd0e9df2e4b7ab1fa8ad` on `tipjar/readme-invitations` (2026-11-03); reader implementation review remains parent-owned.
Verified checkpoint SHA-256 bytes (source filenames relative to repository root):
- `agent_contribute/tipjar.py`: `bcd282ba27be0f3bb30ddf63d19304048e6aeb75eacb18e9d7224200395f196c`.
- `agent_contribute/find.py`: `c6685dfa1c283c08d74509cd96b9b08aa92d66d78129d935f272b7df04e0e29f`.
- `agent_contribute/readme_invitation.py`: `e01638a87a0744925d8929c84d45698228f4a3af9504f057ec5c4344d28fe861`.
- `agent_contribute/schemas/output/4/jar.schema.json`: `0002ca985c747029c3cd3d1df1e58b9bc88ca349e65aa1336beb551d3350447b`.
- `agent_contribute/schemas/output/4/find.schema.json`: `2a23bde107dc0432d3dccdd27e429082cbc7324fb3185d9bf39b3ffbf4d95b40`.
Compared with the initially inspected dirty `17a9258` state: finder, badge parser and both schemas are byte-identical; the only reader difference is compact JSON separators when revalidating manifest bytes in `_complete_report`. Public interfaces are unchanged.
Before coding, parent completes reader/design review and starts from integrated reader + main (including the Python 3.10 compatibility fix); no implementation or workflow activation is authorized by this amendment.

## Exact public interface

- Registry remains `tipjar-board-registry/1`; no new enrollment fields, source approval, scoring, participants or authority.
- New snapshot format is `tipjar-board/2`; `rules_version:1`. Root keys, coverage keys, tips, repositories, checks and directory envelope equal board1 exactly. Only directory `jar`/`source` contracts change.
- `validate_board(data: bytes|dict, *, now=None) -> dict` dispatches strictly on `/1` or `/2`; unknown versions fail closed. `/1` schema and semantic acceptance stay frozen, independent of whichever reader is currently installed.
- `require_fresh(board, *, now=None)` validates either version and rejects expiry; expired served snapshots remain structurally readable for replacement. No snapshots are rewritten or relabeled.
- `collect(registry, client=None, *, now=None, source_commit, controller_id, clock=None) -> dict` deliberately emits `/2` after coordinated integration; existing CLI flags stay unchanged. It calls `read_jar(..., invitation_protocol='tipjar-invitation/2')` explicitly and requires `find-jars-report/2`; future versions are refused.
- `/2` directory observations retain exact `{repository_id,repository,disposition,verified_at,checks,jar,source}` keys. Require public metadata identity/name, raw jar identity and joined repo identity to agree numerically and canonically.
- A complete `/2` raw jar has exactly `{repository,repository_id,default_branch,commit,tree_sha,manifest_present,source_kind,path,blob_sha,sha256,fetched_at,state,complete,manifest,badge,errors,notice}`. Embed the reviewed output4 complete-report alternatives in the board2 schema; omit CLI-only optional `api_budget`.
- Validate `complete:true`, empty errors, UTC reader time, closed bounded fields and nonblank branch/notice. Preserve board1 safe-integer/duplicate-key/UTF-8/future-time checks throughout the raw report. No current-reader validator may reinterpret archived board1 data.
- `/2` non-null `source` is exactly `{kind,path,commit,tree_sha,blob_sha,sha256}` and matches raw jar fields (`kind=source_kind`). Commit/tree/blob SHA are lowercase 40hex; content digest is lowercase 64hex where present.

| Canonical kind | Required raw jar relation | Public source and invitation |
| --- | --- | --- |
| `manifest` | `manifest_present:true`, path `.tipjar.json`, valid manifest matches `welcome|closed`, badge null | All pins present; source kind `manifest`; only welcome supplies invitation CTA |
| `readme` welcome | `manifest_present:false`, path `README.md`, manifest null, badge exactly `{protocol:'readme-welcome/1',repository:canonical-name-lowercase}` | All pins present; source kind `readme`; welcome supplies invitation CTA |
| `readme` undeclared | Same real README path/pins, manifest and badge null, state undeclared | Preserve real README source pins/link; no invitation CTA |
| `absent` | `manifest_present:false`, state undeclared; manifest/badge/path/blob/digest null; commit/tree present | Source kind `absent`, null path/blob/digest, real commit/tree; no file link or invitation CTA |
| unknown/excluded observation | Known public metadata can remain; incomplete/unverified jar is not projected | `jar:null,source:null`; private/moved/conflicting identities follow existing suppression rules |

Source links are constructed only from validated repo/commit/path for `manifest|readme`; never from badge URLs, issue text or arbitrary report URLs. Board code does not fetch an SVG or parse/normalize Markdown.
Closed/invalid/unreadable/unsupported manifests cannot be rescued by a README. Canonical reader alone determines precedence, exact prefix validity, copied-fork mismatch and unknown state. A welcome remains invitation only, never task/execution/publication authorization.

## Global constraints and collector projection

- Keep 500 tips/100 authors/100 curated repos, 1 MiB registry, 4 MiB public snapshot, 200 whole repo groups, 200 observations/1 MiB directory, 5,000 invocations, 8 MiB/30 seconds per invocation and 48-hour expiry.
- Finder2 performs exactly two page-1 searches, at most five hits each, one shared deduplicated candidate pass: manifest query `filename:.tipjar.json path:/`; README query `"tipjar:welcome:v1" filename:README.md path:/`.
- Extend the fixed GET allowlist only for these two encoded search endpoints and `contents/README.md?ref=<40hex>` beside existing pinned routes. Both request methods reserve budget, force one uncached attempt and count failures; never invoke 5,001.
- `search_failed=any(search.errors contains search_failed)`; `server_incomplete=any(incomplete_results===true)`; `truncated=any(truncated===true or short_page===true)`. Preserve both-search failure/partial flags even when no rows survive; no fallback welcomes or prior totals.
- Search observations select candidates only. Every included directory row gets new metadata, explicit invitation2 commit/tree/content reads, and final metadata checks; record every direct read-start in existing `checks`, including README fetch. Do not substitute find completion time or generation time.
- Failed jar reads yield unknown/no CTA with fresh public final metadata; later private observations scrub the entire joined group. Preserve numeric-ID ordering, whole-group caps/omitted counts, per-tip consent/controller/repo/PR minima and earliest-included-read expiry.
- Use a shared fixture corpus to enforce Python/JS agreement on both versions, byte caps, strict numeric tokens, source relationships, timestamps and rank inputs. All new fixtures are visibly FICTIONAL; production registry stays empty.

## Ownership and implementation sequence

### Task 1 — collector/schema owner (this lane after approval)
**Files:** modify `tools/tipjar_board.py`, `tests/test_tipjar_board.py`; create `tools/schemas/tipjar-board-v2.schema.json`, `tests/fixtures/tipjar-board/v2/`; preserve both existing board1 schema files and fixtures.
**Interfaces:** frozen `/1` validator plus closed `/2` dispatcher above; explicit invitation2/find2 collection; same trusted SHA/controller CLI arguments.
- [ ] Add positive/negative matrix cases below, run `python -m unittest tests.test_tipjar_board -v`; expect new `/2` cases FAIL while all archived `/1` cases PASS.
- [ ] Implement only version dispatch, exact projection, endpoint/budget support and two-search flags; consume the reviewed canonical reader without parsing badges.
- [ ] Run focused tests with required locked Ajv; expect PASS. Commit exact schema/fictional fixtures first for downstream consumers, then collector code with tests; parent review gates integration.

### Task 2 — UI owner (separate existing site lane)
**Files:** modify `web/leaderboard-model.js`, `web/leaderboard.js`, `tests/web/leaderboard.test.cjs`; add shared `/2` fixtures; change `web/model.js` only if an existing helper rejects the new complete canonical report.
**Interfaces:** `parseBoard(text, now)` accepts `/1|/2` with version-specific closed schemas; unchanged rankings/periods/eligibility. Render validated README source text/link and invitation only for complete welcome.
- [ ] Add matrix cases and cross-version source-link rendering regressions; run `node tests/web/leaderboard.test.cjs`, expect new `/2` cases FAIL.
- [ ] Implement parser dispatch and text/link projection; preserve CSP, literal rendering, mobile/keyboard behavior, expired-state suppression and old directory-import contracts. Run model/browser checks; expect PASS; commit.

### Task 3 — Pages/controller owner
**Files:** modify `tests/test_tipjar_board_deploy.py` and `tools/tipjar_board_deploy.py` only if its existing imported validator rejects either supported format; modify `MANIFEST.in`, `tools/check_install.py` for new source-only schema/fixtures as appropriate; update `docs/leaderboard.md` for explicit `/2` collection.
**Interfaces:** imported `validate_board` accepts served `/1` and candidate `/2`; generation, trusted current default SHA and expiry gates remain unchanged. Collector/tool code upgrade changes emitted format intentionally; no new workflow flags or activation here.
- [ ] Add old served `/1` → candidate `/2` acceptance, expired served `/1` replacement, malformed candidate and unknown-version refusal tests; verify failure before implementation and PASS afterward.
- [ ] Assemble collector → site → Pages tar → predeploy smoke with fictional `/2` states and empty production registry; no participant submissions. Run full `python -m unittest discover -v` with required Ajv and packaging checks for manifest/install edits; expect PASS.
- [ ] Parent obtains independent implementation review and handles separate publication authority. Do not activate workflows, push, merge or deploy as part of this design task.

## Focused regression matrix and review focus

| Input class | Positive assertion | Negative assertion / owner |
| --- | --- | --- |
| Version isolation | Existing `/1` corpus still parses; valid manifest/README/absent `/2` parses | Unknown `/3`, new jar keys in `/1`, wrong source kind/path/digest/tree/repo reject whole envelope — collector/UI |
| Canonical precedence | Canonical README welcome counts as invitation with real pinned README link | Closed/invalid manifest + README cannot supply CTA; copied fork, malformed/duplicate prefix remains unknown — reader integration/collector/UI |
| Absent/plain source | Absent keeps commit/tree, plain README keeps actual blob/digest, neither suggests work | Invented `.tipjar.json`, source link for absent, incomplete jar/raw errors or forged badge binding rejected/suppressed — collector/UI |
| Two-search coverage | Either search can supply one deduplicated public repo; direct README read affects minimum/expiry | First/second search failure, private/null hits, contradictory IDs, truncation and budget exhaustion stay partial with privacy scrubbing — collector |
| Preserved trust/time | Same eligible tip set yields identical scores for `/1|/2`; old served `/1` can be replaced by fresh `/2` | Edited consent/self-merge/private/future checks, crossed expiry, stale generation/source SHA remain blocked; expired data has no scores/CTA — all owners |

Self-review: no schema/scoring/enrollment migration, no independent badge parser, exact interfaces and owners assigned; immutable reader checkpoint is pinned; parent-owned reader and fresh Terra design reviews remain pre-implementation dependencies.
