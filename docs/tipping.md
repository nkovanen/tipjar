# Give a project something useful

A Tipjar gift is agent work: a small fix, clearer documentation, or a regression
test that a maintainer can review. Start with a project you care about and one
specific improvement. Success is a useful, reviewed draft offered respectfully;
maintainers decide whether to accept it.

## Give a tip with your existing agent

Use the coding agent you already use; Tipjar's CLI and Skill are optional.
You can follow the project's usual contribution process without adopting the
optional verification workflow below.

1. Choose a project and one small improvement. Read its contribution and AI rules,
   check for overlapping work, and agree the permitted scope. Ask maintainers
   before starting wherever their rules require it. Stop for bans, refusals or
   unresolved scope or permission; a welcome alone approves no task.
2. Have your agent explain its plan. Review it and authorize work before it starts.
   Inspect any scripts before running them and keep execution within your actual
   permissions. An invitation does not authorize local execution.
3. Review the result, run the required checks and disclose agent assistance as the
   project requires. Then authorize publication separately through the project's
   usual process. Maintainers decide whether to accept the contribution.
4. If an eligible agent-assisted PR is actually merged, its author may
   [submit that merged tip for curator review](https://github.com/nkovanen/tipjar/issues/new?template=submit-tip.yml).
   Submission promises neither acceptance into the board nor a score.

This ordinary journey is not task 0.3 machine verification. Project rules and
real human authorization still apply without a Tipjar contract.

**Already adopted a task, Skill, or protocol?** Its constraints and gates remain
binding. Do not relabel paused, refused, blocked or pending-authorization work as
“ordinary” to continue. Stop and resolve it through the adopted process; this
guide supplies no override, consent record or permission to bypass a refusal.

## Optional: Tipjar CLI and task 0.3

The following CLI walkthrough is an optional way to prepare and check contribution
records. Choosing this route means following all of its requirements and gates.
There is no native human-consent issuer; an agent must never invent the host
assertions, approval events or consent records this route requires.

**Candidate walkthrough.** These commands describe the unreleased task 0.3
external route. Check `tipjar --help` and `tipjar instructions` against your
installed version first. `agent-contrib` is the equivalent original command name;
from a source checkout use `python3 -m agent_contribute`. CLI, task, evidence and
report schema versions are independent: this route uses task **0.3**, evidence
**0.2**, external-context **0.1**, draft-payload **0.1** and output schemas **4**.
There is no automatic upgrade or built-in human authorization issuer. Unsigned
request views help a host review bindings; they do not issue authorization.

## Path one: give back to something you use

Tell your agent: “Use Tipjar to find a small contribution to owner/project, which
I use. Show me the proposed work and its rules before starting.” This permits
assessment; it does not authorize implementation or publication.

Choose the actual repository from your project's dependency declarations or its
package's repository metadata. Confirm the identity yourself; a familiar package
name is not proof of ownership. The current candidate includes `dependencies`,
`find`, `session`, `init`/`jar-check`, `receipt` and the web directory. Check your
installed CLI's `--help` for version-specific command availability.

```sh
tipjar jar owner/project
tipjar discover owner/project --signals --limit 10
tipjar inspect 'owner/project#12' --ownership
```

`jar` returns `state: welcome|closed|undeclared|unknown`. A complete observation
exits 0 even for `closed`; unknown exits 1. Stop for closed or unknown. Welcome
invites assessment subject to the ordinary contribution rules. Read every source
in `repository_policy`, including applicable linked instructions and owner rules.
Stop for a refusal, ambiguity, incomplete reads, an existing claim or overlapping
PR. Discovery ranking and labels do not supply permission. A limited display is
not evidence that every candidate was shown.

Choose one narrow issue and have the agent explain the behavior it will change,
the tests it will run, and what it will leave alone. Continue to the shared
handoff below only after that assessment is clear.

## Path two: explicitly choose a repository with no declared invitation

Tell your agent: “Assess owner/project#12 for a possible Tipjar gift. I know it
has no declared invitation; show me its policies and the proposed change first.”

```sh
tipjar jar owner/project
tipjar discover owner/project --signals --limit 10
tipjar inspect 'owner/project#12' --ownership
```

For this current invitation2 path the pinned observation must be complete and
`undeclared`: no manifest is present, and a plain README has no declared welcome
or invitation files are absent. Invalid or copied README badges remain `unknown`,
not undeclared. Historical task schemas 0.1/0.2 retain manifest-only resolution.
Absence grants no maintainer approval.
Do not use `--welcomed-only` for this explicitly selected path. Review all the
same source and fork policies and overlap checks as in path one. A human may
choose to offer a policy-compliant draft that maintainers can decline; a ban or
unresolved condition still stops the journey. The later implementation **and**
publication assertions must both acknowledge the undeclared invitation basis.

## From one selected issue to one reviewed draft

Use a personal immediate public fork of the source, a new branch, and the source
default base. Organization forks, prior work adoption, alternate bases and draft
updates are unsupported. Creating the fork and checkout uses the host's ordinary
tools and actual authority; the CLI creates neither. Keep all JSON records in a
separate working directory outside the implementation checkout. Below,
`CHECKOUT` is that checkout, `SOURCE_SHA` is the task's exact source commit,
`alice/project` is your actual fork, and `tip-12` is its exact new branch name.

```sh
tipjar prepare 'owner/project#12' --schema-version 0.3 --fork alice/project --head-ref tip-12 --output task.json
tipjar lint task.json
```

Successful preparation exits 0 with `contract.schema_version: "0.3"`; it writes
a pending draft, not permission. Initial lint exits 1. Review and refine the
contract's scope, behavior criteria, validation argv, prerequisites and
source-linked requirements ledger, then lint again. A reviewed lint pass exits
0; it does not grant authority or establish that prose requirements are true.
Never execute validation argv merely because it appears in a contract.

Ask the CLI for an unsigned review view after preparing the assessment and
retaining the original ledger bytes:

```sh
tipjar drift task.json
tipjar authorization-request task.json --repo-dir CHECKOUT --policy-assessment assessment.json --policy-ledger policy.md
```

The request contains the contract, source/fork inventory and supplied assessment/
ledger hashes, actor and refs, invitation basis and pending gates. Omit the two
policy inputs to inspect an initial view with those hashes explicitly unresolved.
Exit 0 means its live reads completed; `issued` and `ready_for_issuance` are always
false. Neither the request nor its `bindings` object is valid authorization.
The drift report compares source policy and jar state with the task; the fork
hash must be compared with the host's retained record because tasks store no
fork baseline. External targets still require real manual rereads.

**Stop for implementation authorization.** The actual human/host must issue and
retain the external-context record outside worker control. The agent may relay
that record unchanged. Both source and fork inventories need complete,
digest-bound policy assessments, with actual referring context and target reads;
ordinary references cannot simply be dropped. Include fresh host observations
of every applicable target. The implementation assertion binds the exact task,
actor, both inventories, assessment, original ledger bytes and invitation basis,
with actions exactly `["implement"]`. For no-jar selection,
`undeclared_acknowledged` is true; for welcome it is false. Follow the exact
[external route record requirements](external-tips.md), not a made-up approval
field or a test fixture.

```sh
tipjar verify task.json --stage implementation --repo-dir CHECKOUT --host-context-stdin < implementation-context.json
```

Exit 0 with `implementation_ready: true` passes this gate only. The checkout must
be clean at the source commit, on the new named branch with a matching fork
remote and no published branch. Resolve all blockers before work. Within actual
execution authority, inspect scripts, implement the narrow change, run every
required validation, and obtain independent review after final validations.

```sh
tipjar scope-check task.json --repo-dir CHECKOUT --base SOURCE_SHA
tipjar evidence init task.json --repo-dir CHECKOUT --base SOURCE_SHA --output evidence.json
```

A passing scope report exits 0 with `within_scope: true`. Evidence initialization
also exits 0, but returns `evidence_valid: false`: evidence 0.2 has pending review
and unfilled results. Fill those from actual runs and reviews. Retain the original
policy ledger as an artifact plus final compliance bound to the final head.
The CLI runs no validation commands and cannot prove review independence.

Render a reviewable starting body:

```sh
tipjar pr-body task.json --evidence evidence.json --repo-dir CHECKOUT --output body.md
```

This writes a new file exclusively, reports its exact UTF-8 byte hash, and lists
pending host-context gates. It does not reproduce a host-authorized verification
run. Merge the applicable template content, review the disclosure and results,
then prepare a draft-payload 0.1 JSON file with the exact reviewed title and body,
`draft: true` and `maintainer_can_modify: false`. Include actual agent disclosure,
validation results and the applicable source PR template. Hashes bind parsed
payload strings; changing the body later requires a new publication decision.

Inspect an unsigned view bound to the completed evidence and exact payload:

```sh
tipjar authorization-request task.json --stage draft --repo-dir CHECKOUT --evidence evidence.json --publication-payload payload.json --policy-assessment assessment.json --policy-ledger policy.md
```

It computes evidence/review/payload hashes and shows the exact head/tree and
observed source tip. The requested actions are `["push_head", "create_draft"]`;
they are a request, not permission. Policy/evidence diagnostics remain untrusted.

**Stop for publication authorization.** After validation and independent review,
the human/host issues a separate assertion bound to exact evidence, review,
head/tree, source base tip and payload. Actions are exactly
`["push_head", "create_draft"]`. Retain the new actual decision event separately
from implementation authorization. Add fresh policy observations; do not reuse
expired observations or manufacture consent to make a gate green.

```sh
tipjar verify task.json --stage draft --repo-dir CHECKOUT --evidence evidence.json --publication-payload payload.json --host-context-stdin < publication-context.json
```

Exit 0 with `draft_create_ready: true` permits only the separately authorized
host actions. Rerun immediately before those actions and after the exact push.
The host pushes the exact head and creates the exact upstream draft using its
own tools. The CLI never writes to GitHub. Add the observed numeric PR identity
as the host's untrusted publication claim, refresh observations, then recognize it:

```sh
tipjar verify task.json --stage published --repo-dir CHECKOUT --evidence evidence.json --publication-payload payload.json --host-context-stdin < published-context.json
```

Exit 0 with `publication_verified: true`, `next_action: "return_draft"` and the
PR URL means return that draft to the human. It does not mean acceptance,
completion, ready, merge, release or permission to update it.

## Current helper behavior and observed exits

The offline helper matrix uses real temporary Git repositories and synthetic
GitHub/host records for both welcome and undeclared paths. Those fixtures prove
interoperability, not human consent, actual product test execution or live
publication. In this candidate every tested helper returns JSON without crashing:

| Command with task 0.3 | Observed exit/result |
| --- | --- |
| `prepare` | 0; pending task 0.3 |
| `lint` | 1 pending, 0 after contract review |
| `scope-check` | 0 for in-scope fixture change |
| `evidence init` | 0; `evidence_valid: false`, pending evidence 0.2 |
| `verify --stage implementation` | 0 with synthetic bound host context |
| `verify --stage draft` | 1 with skeleton, 0 with completed synthetic evidence/context |
| `verify --stage published` | 0 with matching synthetic draft/claim |
| `drift` | 0 for complete unchanged fixture; reports source/inventory/jar comparisons |
| `pr-body` | 0; new reviewable body, no publication; existing output refused |
| `authorization-request` | 0 for complete unsigned view; issuance remains false |
| `schema prepare` (and schemas for helpers above) | 0; packaged JSON Schema |

Completing this optional task 0.3 route requires a host that can issue real bound
records after actual human decisions. The CLI now prepares unsigned review views;
there is no native issuer. Do not synthesize consent or substitute a task 0.2
mandate. Source drift is report-only, and PR body/payload composition still needs
review and applicable template content. Use `tipjar schema authorization-request`,
`tipjar schema drift`, `tipjar schema verify` and canonical JSON for full fields;
text output is abridged. Task 0.3 `pr-body --closes` is unsupported (exit 2).

## Maintainers: invite the kind of help you want

Publish a reviewed `.tipjar.json` at your repository root on the default branch:

```json
{"schema_version":"0.1","status":"welcome","wanted":["Small bug fixes with regressions"],"boundaries":["Read CONTRIBUTING.md and disclose agent assistance"]}
```

State your actual tests, review expectations and agent policy in normal
contribution documentation too. A jar does not install an agent, accept money,
approve issues or promise acceptance. Use `status: "closed"` to declare an
opt-out; older clients may not enforce it. Publishing the file is your decision.
Inspect what contributors see with `tipjar jar owner/project` and
`tipjar audit owner/project`. The separate label-approval policy is optional and
has its own authority tradeoffs; see [maintainer integration](maintainers.md).
