# Tipjar submission intake helper — design proposal

Status: docs only, based on `fbb0af68cb6b668c6db2edc1863a2ddc50a0ca30`; parent owns Terra design review and implementation authorization.
Goal: let a human curator review one public submission with correct numeric pins and an exact body digest, without assembling them by hand.
No implementation, enrollment, registry edit, publication, GitHub write, third-party contact, or native consent issuer is authorized by this proposal.

## Smallest interface and alternatives

Proposed source-only command (design choice, not an installed CLI addition):
`python3 tools/tipjar_board_intake.py --submission ISSUE_NUMBER --pull-request 'owner/repo#N' --output FILE`.
Use the existing ASCII positive 1–10-digit issue/reference limit; fixed controller `nkovanen/tipjar`, numeric ID `1444643470`, with no controller override.
Explicit PR input prevents issue text, Markdown links or checkboxes from selecting fetch routes.
A documented `gh`/hash recipe is smaller but preserves the copying/hash mistakes this task addresses; parsing issue forms automatically would confuse text with consent.
Choose a single-candidate helper; defer batch intake, registry lookup, approval switches, web UI and another public protocol.
Registry stays `tipjar-board-registry/1`; board1/board2 eligibility, scoring, formats and predeploy gates are unchanged. No invitation/finder reads are needed.

## Reads and mechanical checks

Reuse `core.parse_issue`, `tools.tipjar_board.BudgetClient(limit=7)`, `receipts.observe`, and existing `_public_meta`/`_tip` live checks.
Keep shared helper use inside source tooling; do not change installed library behavior or fork eligibility logic into a second implementation.
Exactly these GETs on a successful attempt; failures stop immediately, with at most seven actual `gh` invocations:
1. `repos/nkovanen/tipjar`: verify fixed numeric/canonical controller identity, `private:false`, `visibility:public`.
2. `repos/nkovanen/tipjar/issues/{submission}`: validate positive safe issue ID/number, canonical constructed URL, User actor ID and string body; reject PR-shaped issues.
3. `repos/{explicit-repo}`: `receipts.observe` validates current exact canonical name and public repository numeric identity.
4. `repos/{explicit-repo}/pulls/{N}`: same call validates PR number/URL/ID, public matching base repo and consistent closed, non-draft merged facts.
5. Re-read the submission; require unchanged issue ID/number/URL, User actor ID and exact body string.
6. Re-read receiving repo; require unchanged numeric/canonical/owner identity and explicit public visibility.
7. Re-read controller metadata; require the same fixed public controller identity.
All IDs must be positive safe integers excluding booleans. Issue actor ID must equal PR author ID; both must be User, not Bot.
Apply current board checks for future/inconsistent merge timestamp, closure, merge commit and merger; merger ID and receiving owner ID must differ from author ID.
Use `_tip` only to check observed PR eligibility, not to assert the missing human declarations. Discard its public-row projection.
No cache/application retries, search, pagination, saved receipt import, arbitrary URLs, head-repo fetch or PR/issue commands. Existing 8 MiB/30-second per-invocation transport caps apply; failures consume budget.
A rename/transfer/canonical-case mismatch fails with a generic retry/review message; never silently follow a changed name or invent ID lookup routes.
These reads are non-atomic. Final public checks reduce exposure; they cannot prove uninterrupted public visibility, independence, consent truth or permanence of a merge.

## Local candidate, never an accepted tip

Design choice: one closed, source-only JSON envelope `format:'tipjar-board-intake/1'`, unrelated to public/CLI schemas.
Exact root keys: `format`, `status`, `generated_at`, `checks`, `pins`, `submission_body`, `review_checklist`.
`status` is always `review-required`; `generated_at` is canonical UTC Z, after all successful reads, never a freshness authorization.
`checks` is the seven read-start UTC timestamps in the fixed order above; `submission_body` is the original decoded REST body string, unmodified.
`pins` contains exactly `repository_id,repository,pull_request_id,number,author_id,submission`.
Its `submission` contains exactly registry1's `controller_repository,controller_repository_id,issue_id,number,body_sha256` fields.
Calculate `body_sha256 = hashlib.sha256(body.encode('utf-8')).hexdigest()` without newline/Unicode normalization, trimming or hashing raw JSON; invalid Unicode encoding fails.
The digest identifies saved bytes only; it proves neither review nor consent. Exact body and digest stay together for the later human semantic review.
Do not output `agent_assistance` or `author_controls_repository`, even when checkbox text appears present. Candidate pins alone intentionally fail registry tip validation.
`review_checklist` is a fixed array of five advisory strings, never parsed from issue text or recorded as completed:
1. Review the saved untrusted body literally: it names the explicit PR and clearly opts in that PR/identity/proof/merge/size data; no withdrawal or contradictory text.
2. Verify explicit self-declared assistance and no control of the receiving repository/organization/project; public owner inequality does not prove independence.
3. Review known reverts, split/duplicate/farming concerns and authenticated owner opt-outs; inspect current exclusions and all other consent entries for this PR.
4. Check registry conflicts by numeric repo/PR key, PR number/author/name bindings and submission issue identity/body digest; validate the complete proposed registry offline.
5. Refresh intake before acceptance; authorize the registry edit/publication separately, then let the normal collector re-read every pin before counting.
Human acceptance alone adds `agent_assistance:'self-declared'` and `author_controls_repository:false` to the copied pins after reviewing those declarations.
Never infer either field from an unchecked/checked box, issue title, author association, exit code, matching hash, or a prior candidate file.

## Failure, privacy and output

Validate bounded inputs/output destination before any GET. Buffer and validate the full candidate before creating output; no partial candidate on failed reads.
Bound body UTF-8 to 256 KiB and final encoded candidate to 2 MiB; enforce limits before hashing/saving and reject recursive duplicate keys/nonfinite JSON through the transport.
Create only the explicit new local file with exclusive creation and mode 0600; reject an existing file, symlink (including dangling), nonregular destination or missing parent.
Never overwrite, follow a symlink destination or modify the production registry; remove only this invocation's incomplete newly created output on write failure.
Prefer the repository's existing safe file patterns; symlink-free parent checks are required, not a hostile-filesystem sandbox or guarantee against same-user mutation.
Exit 0 means candidate saved for review, 1 means incomplete/refused/write failure, 2 means invalid CLI use. Failures emit fixed categories, no raw API errors, issue body or private response payloads.
Success stdout contains only the review-required status and output path; never raw body/terminal escapes, consent/independence claims, points or enrollment claims.
Keep the artifact outside the repo and site; it includes public issue text and is not an upload, evidence of execution, authorization, or input accepted by the collector.
Review the JSON string as untrusted text; never render its HTML, execute it, follow embedded commands/URLs or allow it to change the curator's instructions.
An issue edit before/during collection fails the final comparison; an edit after output invalidates the saved digest at normal collection until reviewed again.
Closing a submission is not withdrawal. A separate still-valid consent can qualify the same PR; withdrawing a tip requires removing/excluding all consent entries under existing rules.
No registry input means no automated “new/duplicate/eligible for enrollment” verdict. Same PR in multiple candidates remains one numeric dedup key and at most one point.

## Acceptance matrix for a later implementation

| Fixture / operation | Required observable result |
| --- | --- |
| Public merged PR + matching public issue User | Seven GETs only; saved review-required pins/body/digest are exact; declaration fields absent; collector rejects artifact as registry input |
| CRLF, trailing newline, non-ASCII and combining Unicode body | Hash exact decoded UTF-8 bytes; no normalization; saved body round-trips byte-for-byte |
| Missing/non-string body, bad Unicode, 256 KiB+1 body, oversized envelope | Exit 1, no output, no raw payload in diagnostics |
| Wrong controller ID/name/public flags, PR-shaped issue, URL/number/ID mismatch | Fail closed before any candidate write; no issue-selected routes |
| Different issue/PR author, bot, self-owned or self-merged, unmerged/draft/future/inconsistent merge | Refuse with no candidate or approval claim |
| Private/internal/missing repo or base, or final repo/controller becomes private | No candidate or retained private payload; generic error only |
| Body/actor/issue identity changes at final read | Refuse; later edits fail the normal registry digest check rather than silently updating pins |
| Missing/unchecked boxes, contradictory declaration or withdrawal text | Mechanically valid observations may produce review-required candidate; no semantic pass, declarations, enrollment or automatic registry edit |
| Existing same PR via another issue, conflicting pins, exclusion or reverted PR | No duplicate/independence verdict; human checklist requires full-registry conflict/exclusion review; collector still dedups/excludes normally |
| 403/404/429/timeout, malformed/duplicate-key API JSON, budget exhaustion | At most seven invocations, no retry/search/fallback/partial candidate; exit 1 |
| Existing output, dangling symlink, unsafe parent, write failure | Preserve existing target bytes; refuse unsafe path; clean up only newly created incomplete file |
| Hostile Markdown/HTML/shell/terminal escapes, explicit PR differs from body link | Fetch only explicit validated reference; save body literally as JSON; no execution/rendering or unsafe stdout; human resolves mismatch |

## Later implementation boundary

After design approval, the smallest implementation task creates `tools/tipjar_board_intake.py` and `tests/test_tipjar_board_intake.py`, and updates only the curator section in `docs/leaderboard.md`.
Expose `intake(submission:int, reference:str, client=None, *, clock=None)->dict` for deterministic fake-GET tests; CLI owns bounded exclusive output.
Start with the matrix's exact-byte, changed-body, private-final-read and no-declaration red cases, then reuse existing checks and prove green; no live participant fixtures.
Run focused tests, full `python3 -m unittest discover -v` with required locked Ajv, then independent input/authority review. If shipping in sdist, update `MANIFEST.in`/`tools/check_install.py` and run packaging checks; never add to wheel.
Parent owns a separate implementation plan and Terra review; this document does not activate or expand existing Pages authorization.
