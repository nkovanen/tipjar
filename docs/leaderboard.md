# Tipjar public board operations

The board at <https://nkovanen.github.io/tipjar/> joins people giving back,
most tipped projects, and freshly verified welcoming jars. A tip is agent-assisted
work, not money. The pilot uses curated public opt-ins and partial coverage.
One distinct eligible merge earns one point; points measure neither value nor
verified AI use. No adoption is implied by an empty registry or directory search.

The collector and deploy checker are source-only tools, independent of the
installed CLI. Their formats (`tipjar-board-registry/1`, `tipjar-board/1`) do not
change CLI, task, evidence, or receipt schemas. The exact closed contracts are
[registry schema](../tools/schemas/tipjar-board-registry.schema.json) and
[snapshot schema](../tools/schemas/tipjar-board.schema.json). Unknown formats,
extra fields, duplicate JSON keys, conflicting identities, unsafe integers,
invalid timestamps, or future checks reject the envelope. Offline receipts and
impact reports never supply scoring authority.

## Submit and curate one accepted tip

Use the controller repository's [submission form](https://github.com/nkovanen/tipjar/issues/new?template=submit-tip.yml).
The reviewed form source is [inert until controller activation](examples/submit-tip.yml.disabled).
Submit through the same GitHub account that authored the PR. The declaration
explicitly opts in that PR and its public identity/proof/merge facts/size context,
self-declares agent assistance and no control of the receiving repository,
organization, or project. It explains editing, withdrawal, expiry, and retained
history. A form checkbox is untrusted data; GitHub authenticates the issue actor,
not the truth of the claim or the independence of the receiving project.

A curator reviews the public issue and actual PR before manually proposing a
registry change. Issue text never changes the registry by itself. Pin these facts:

1. Numeric repository and PR IDs, current canonical `owner/repo`, PR number,
   numeric PR author ID, and the explicit declarations. The author must be a
   GitHub User, not a bot. Author and repo owner IDs must differ; exclude known
   author-controlled projects and coordinated farming. Public metadata cannot
   prove organizational independence or detect all collusion.
2. Submission issue numeric ID, number, author matching the PR author, fixed
   controller name `nkovanen/tipjar` and numeric ID `1444643470`. Reject PR-shaped
   issue responses. A supplied proof URL is never authority; proof is constructed
   under `https://github.com/nkovanen/tipjar/issues/`.
3. SHA-256 of exactly `body.encode('utf-8')` from the decoded REST issue `body`
   string. Preserve all whitespace, newline and Unicode bytes; never normalize.
   Missing or non-string bodies fail. Do not hash the raw JSON, rendered Markdown,
   issue title, or a copied browser selection.

Use authenticated read-only GitHub GETs to review those facts. Store the reviewed
pins in [the production registry](examples/tipjar-board-registry.json), currently
empty. `tips` contains the exact identity/submission fields in the schema;
`repositories` is an optional curated candidate list, not asserted welcomes;
`exclusions` records fixed reason codes. No score overrides exist. Keep review
notes and generated evidence outside the repository. A registry edit needs normal
human review and controller publication authority; it cannot authorize code
execution in another project.

On each refresh the collector rechecks controller public identity, consent
issue/actor/body digest, repository and PR public identity, closed non-draft merged
state, consistent merge timestamp/commit/merger, and all exclusions. Merger and
author numeric IDs must differ; that is an acceptance signal, not proof of
independent judgment or protocol compliance. All required reads must succeed for
a tip to count. Canonical-name changes pause counting until a curator updates
the lookup hint and fresh reads confirm the same numeric ID. No undocumented
numeric-ID lookup route substitutes for that review.

The key `(repository_id, pull_request_id)` counts once globally. Consistent
multiple submissions can be checked separately: one fresh valid consent suffices,
never more than one point. Contradictory number/author/name/identity pins reject
the registry. Rankings derive from eligible tips, use merge time for UTC calendar
month, rolling 30 days and all-time, and share rank on ties with numeric-ID order.
Size context is nullable GitHub-reported additions/deletions/files, never points.

## Withdrawal, opt-out and failure

To withdraw, edit the submission to clearly withdraw and notify curators on the
issue. An edit invalidates its reviewed body digest at the next refresh. Curators
remove every consent entry for the withdrawn tip or add a `withdrawal` exclusion;
another valid reviewed submission could otherwise still qualify it. Closing an
accepted issue does not withdraw it. Curator edits also invalidate its digest:
review the complete body and update the pin only when the declarations still hold.

Repository owners/maintainers can [request an opt-out or report a concern](https://github.com/nkovanen/tipjar/issues/new).
Curators independently verify the requester's current role; public author
association alone does not establish it. A repository opt-out removes the repo
from all current views. Exclusion reasons are `withdrawal`, `owner_opt_out`,
`controlled_repository`, `coordinated_farming`, `duplicate_or_split`, `reverted`,
and `curator_exclusion`. Reverts require human review; no commit-message heuristic
or automatic subtraction claims to prove continued presence in the codebase.

A closed, missing or unknown welcome jar removes invitations, not a separately
fresh eligible historical merge. No jar grants source/task approval, local
execution permission, or publication authority. The directory uses canonical
reader observations, not its own badge parser. Board version 1 supports only the
manifest source `.tipjar.json`; future invitation syntaxes need separate review.

Withdrawals apply on successful refresh; failures can delay removal until
displayed expiry. Historical copies may remain in issues, registry history,
artifacts and browser caches. There is no promise of instant removal or historical
erasure. At expiry the UI hides scores and welcome actions and says refresh is
overdue. A failed collection never replaces old data with fabricated empty totals
or fictional fixtures.

Malformed registry/envelope or collector-wide failure produces no publication.
Per-item failures, missing/private/deleted repositories, invalid consent or rate
limits suppress the affected row and expose only aggregate unknown/excluded
counts. Other verified rows can publish as partial coverage; totals may decrease.
Do not publish private identifiers or raw failure payloads. Exclusions are curator
decisions; unknowns are incomplete observations, never permissions or approvals.

## Bounds and freshness

The registry is at most 1 MiB, 500 tips, 100 authors, 100 curated repos. Public JSON
is at most 4 MiB, 500 tips and 200 repository rows; directory projection is at most
200 observations and 1 MiB. Whole repository groups are admitted by ascending
numeric ID, skipping a group that cannot fit and continuing; omitted counts are
separate from unknowns. This bounded selection biases rankings. Search is one
indexed batch and never an exhaustive directory. Even an empty pilot performs
a fresh bounded search; it does not publish a stale template as a fresh snapshot.

Collection uses one uncached budget client, at most 5,000 actual `gh` invocations,
one attempt per read, with failed attempts consuming budget and the existing
8 MiB/30-second invocation caps. Size fields reuse the same PR response. No
arbitrary URLs, retries, cached receipts, issue commands, PR code, or other
projects' checkout/build scripts are executed.

Every required read records its UTC start. Tip `verified_at` is the minimum of
consent/controller/repository/PR checks; directory checks include every required
read, including final metadata. `expires_at` is the earliest included tip check,
repo verification or directory check plus 48 hours. With no included observations
it is generation plus 48 hours. All checks must precede generation, which cannot
be future. Recheck after collection, after site assembly and immediately before
deployment. These are non-atomic public observations, not continuous guarantees.

## Reviewed workflow and controller activation

[The workflow example](examples/tipjar-board-pages.yml.disabled) is inert. It
runs daily and manually after activation. It checks out the trusted default-branch
commit with credentials disabled, collects with job-scoped `GH_TOKEN` and only
`contents: read`, copies `web/` unchanged to the site root, and adds `board.json`.
No frontend build or external dependency install is required. It uploads a Pages
`artifact.tar` and a separate trusted checker bundle from that same checkout.
The bundle contains source tools, schemas and normal library resources; it is
not part of the public site. No browser token, server, payment flow or account
system is involved. Preserve project-subpath assets and the local directory's
no-fetch policy; the public board fetches only relative `board.json`.

Inherited workflow permissions are cleared. Only the deploy job receives
`pages: write` and `id-token: write`, behind the protected `github-pages`
environment and successful build. It has no checkout, `GH_TOKEN`, PAT, contents
permission or arbitrary fetch input. Artifact downloads are from the same run.
Every publisher must use fixed whole-workflow concurrency group `tipjar-pages`,
with `cancel-in-progress: false`. Ordering is not guaranteed: generation checks
are still required, and unrelated publishers must not bypass this serialization.

Immediately before `deploy-pages`, the checker reads root `board.json` directly
from the downloaded Pages tar without extracting it (64 MiB archive, at most
1,000 members, one regular root board, no duplicate aliases). It validates the
candidate and current served board against the same closed contract. The current
board may be expired so a fresh replacement can recover; the candidate must be
fresh, from the current trusted default-branch SHA, and strictly newer than served
generation. A delayed or reordered artifact therefore cannot restore older data.
The predeploy source check makes at most two unauthenticated, uncached public
GitHub GETs against fixed controller routes, separate from the collector budget
(8 MiB/30 seconds each, including a Linux wall-clock interrupt for DNS and headers). The served state is one bounded 4 MiB/30-second request
to exactly `https://nkovanen.github.io/tipjar/board.json`. Redirects, unreadable or
malformed state block. There is no retry, fallback host or user-supplied URL.
Only an explicit controller first-deployment `bootstrap` dispatch permits HTTP
404; it cannot excuse other statuses, bad data, an expired candidate or stale SHA.
Later ordinary dispatches leave bootstrap false. Never use it to recover from a
missing existing deployment without investigating that loss.

Controller activation after independent implementation review:

1. Integrate collector, frontend, checker, registry and source packaging policy.
   Run the required unit/Ajv/Node checks and standalone package checks; inspect
   a local assembled artifact with an honest fresh empty/partial snapshot.
2. Enable Pages with GitHub Actions as its source. Protect `github-pages` for the
   trusted default branch with the intended human deployment review policy.
   Ensure no other workflow or branch publisher can bypass the concurrency group.
3. Copy the reviewed disabled workflow to `.github/workflows/tipjar-board-pages.yml`
   and the reviewed form to `.github/ISSUE_TEMPLATE/submit-tip.yml`. Review these
   as active configuration. Keep the native test/package CI and release policy.
4. Dispatch on the trusted default branch. Use bootstrap only for the first
   expected 404. Wait for deployment success, then verify the exact root URL,
   relative assets/JSON, source SHA, generation/expiry, joined views at desktop
   and 390px, keyboard controls and empty/partial/expiry behavior. Use fictional
   local fixtures for state exercises, never fabricated production scores.
5. Add the prominent top README link to `https://nkovanen.github.io/tipjar/` and
   record the deployed SHA, workflow run, URL and actual verification outside the
   repo. No release, maintainer contact or participation claim follows from deploy.

For a local assembled snapshot freshness check:

```sh
python3 tools/tipjar_board.py --registry docs/examples/tipjar-board-registry.json \
  --output /tmp/board.json --source-commit "$TRUSTED_CHECKOUT_SHA" \
  --controller-id 1444643470
python3 tools/tipjar_board_deploy.py --board /tmp/board.json \
  --source-commit "$TRUSTED_CHECKOUT_SHA"
```

Choose a new output path; the collector refuses overwrite. `TRUSTED_CHECKOUT_SHA`
is the reviewed full 40-hex controller checkout commit, explicitly supplied by the
host/workflow. Do not infer it from registry content or a participant's repository.

Action pins were resolved from official repository tag APIs on 2026-11-03:
[checkout v4.3.1](https://github.com/actions/checkout/tree/34e114876b0b11c390a56381ad16ebd13914f8d5),
[setup-python v5.6.0](https://github.com/actions/setup-python/tree/a26af69be951a213d495a4c3e4e4022e16d87065),
[upload-artifact v4.6.2](https://github.com/actions/upload-artifact/tree/ea165f8d65b6e75b540449e92b4886f43607fa02),
[download-artifact v4.3.0](https://github.com/actions/download-artifact/tree/d3f86a106a0bac45b974a628896c90dbdf5c8093),
[deploy-pages v4.0.5](https://github.com/actions/deploy-pages/tree/d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e).
The workflow creates the official Pages tar layout itself and pins the uploader
directly, avoiding `upload-pages-artifact` v3.0.1's floating nested `upload-artifact@v4`.
See GitHub's [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages),
[concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
and [token permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).
A full SHA is an immutable selection, not proof that upstream code is safe;
review pins and transitive behavior before updating them.
