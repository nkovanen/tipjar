# Maintainer integration

Welcome useful agent work with a README badge or a root `.tipjar.json` on your
default branch. An invitation helps contributors find your project; it does not
approve an issue, authorize local execution or grant permission to publish a PR.
Keep your actual contribution rules explicit in CONTRIBUTING.md.

Use a reviewed [0.3.0 candidate](installation.md); it is unreleased. The published
v0.2.0 has no `tipjar` alias or invitation commands.

## Welcome tips with your README

Generate the repository-scoped snippet offline:

```sh
tipjar --format text badge owner/repo
```

Copy the three-line snippet at the start of the output, including its blank
third line, to byte zero of root README.md. Leave the following notice out of
your README. The default JSON output carries the same snippet in `snippet`.
See [README invitations](readme-invitations.md) for the supported prefix, source binding and copied-fork handling. If you prefer your project title first,
use the manifest below. `.tipjar.json` always takes precedence, including a
closed or invalid manifest; a README welcome cannot override it.

## Repository jars

A root `.tipjar.json` declares `welcome` or `closed` for useful **agent work**.
It does not accept money or execute commands. Wanted work is a preference;
boundaries are untrusted policy-review data, never executable instructions.
A missing invitation is undeclared, not refusal or approval.

### Two-minute setup (offline)

No GitHub authentication is needed to create and check a local manifest. Choose
a state explicitly:

```sh
# Welcome useful agent work; creates a new file, never overwrites one.
tipjar init --status welcome --output .tipjar.json
# Edit wanted and boundaries to match your actual policies before publishing.
tipjar jar-check .tipjar.json
```

Replace the template's `EDIT before publishing` wanted entry with concrete work,
such as a broken documentation example or a small bug with a regression. Review
every boundary, require your contribution guide, and preserve separate human
authorization for local execution and publication. Validation checks structure,
not whether the text expresses your intended policy or approves a task.

To decline agent contributions, choose a closed template instead:

```sh
# Alternative to the welcome command, in a directory without .tipjar.json:
tipjar init --status closed --output .tipjar.json
tipjar jar-check .tipjar.json
```

Existing files and symlinks are refused. Edit an existing file deliberately and
check it again, or use a staging path with `--output`. Neither command reads
GitHub, publishes a file or grants authority. See
[offline manifest commands](cli.md#offline-manifest-setup-and-validation) for
validation limits and the [manifest schema](../agent_contribute/tipjar.schema.json)
for fields.

### Check the published invitation with a fresh read

After you deliberately commit the reviewed README or `.tipjar.json` to your
default branch, inspect what contributors will see:

```sh
tipjar jar owner/repo
tipjar find --owner owner
```

`jar` reads the named repository directly at a pinned default-branch commit and
reports the source path, state and verified blob/digest. It stays fresh even
with `--cache`. `find` verifies one bounded batch of at most ten indexed public
candidates across manifest and README searches; indexing may lag or omit your
project. Neither command registers a project or grants authority. See
[jar inspection](cli.md#jar-inspection) and [find limits](cli.md#find).

Current discovery, preparation and live gates enforce applicable closed/unknown
invitations on the actual issue source, including when resolving a tracker fork.
A fork's welcome or issue approval cannot override a source refusal. Current
public reads and task 0.3 recognize README invitations; published task schemas
0.1/0.2 retain manifest-only resolution and historical inventories. Older CLI
releases do not enforce jars at all, so keep refusals in ordinary contribution
docs as well. Welcome never waives contradictory policies or supplies execution
or publication authority. Outside contributors should follow the separately
reviewed [task 0.3 external-tip route](external-tips.md).

## Optional issue approval through labels

If your project accepts this authority model, commit `.agent-contrib.json` on
your default branch:

```json
{
  "schema_version": "0.1",
  "agent_approved_labels": ["agent-approved"],
  "label_authority": "repository-label-permission"
}
```

Apply a designated label only to tasks with clear scope, acceptance criteria,
validation and prohibited changes. Generic triage labels such as `bug`,
`help wanted` and `good first issue` cannot be used as approval labels.

**The CLI checks that a configured label is currently present on the issue
under the default-branch policy; it does not verify who applied it.** The policy
therefore delegates approval to every account GitHub permits to label issues.
It is suitable only if every principal who can label issues is trusted to
approve agent work. That includes triage, write and higher roles, custom roles
or grants that allow labelling, and any app or automation with label access. A
dedicated label name restricts nothing, and removing triage access alone is not
enough while an untrusted write collaborator or app can still label. If you
need narrower or signed approval, do not opt in under this policy; issues stay
candidates.

Actor verification is not available, and this project offers no
maintainer-only label policy ([#9](https://github.com/nkovanen/agent-contrib/issues/9)).
GitHub's public REST data cannot establish who may approve: `labeled` events
carry no role or author association and no durable label identity, and only a
credential with push access can read a collaborator's role. For work by your
own agents, use the schema 0.2 mandate route
([host authorization](host-authorization.md)) instead of label approval.

A malformed or unreadable policy is unknown, not an invitation to proceed.
Verification rereads current policy and labels.

Repository approval identifies eligible work; it does not authorize the
contributor's local execution, open a PR, replace human review or promise
acceptance. User authorization must independently cover the implementation and
publication target. Resolving a fork's parent never grants either permission.

## See your contribution rules as an agent does

Discovery works without adding configuration to your repository. Tipjar reads
issues, open PRs, root contribution policies, nested AGENTS.md/CLAUDE.md and
specification/architecture indexes from the observed default-branch commit.
Agents must read relevant specification contents and obey your actual rules.
Existing labels alone do not authorize agent-generated work.

`agent-contrib audit owner/repo` is a read-only report that uses exactly the
reads `discover` makes. It shows the policy state and why a policy is invalid
or unknown, approval labels the policy names but the repository lacks, generic
labels used as approval labels, malformed label names (which make the report
incomplete), instruction files agents load, and for each expected kind
(contributing guide, AGENTS.md/CLAUDE.md, pull request template,
architecture/spec index) whether it is `loaded`, `present_unread` (in the tree
but not among the files agents read), `missing` or `unknown` (tree incomplete),
the 60-file instruction cap and whether the tree read was complete. It also counts open issues by ambiguity and approval
state, excluded and overlapping issues, open PRs and overlap density, and shows
fork/tracker resolution. Suggestions are non-binding. `--print-policy` adds a
valid policy template to the JSON output; nothing is written to the repository.
Exit 1 means some read was incomplete.

## Check agent PRs passively (report only)

The candidate includes a report-only GitHub Action, slice 1 (#11), in
`actions/verify/`; copy [the example workflow](examples/agent-contrib-verify.yml)
and pin a reviewed commit. On `pull_request` it reads only the event payload and
the PR-head checkout, with `contents: read` and no API calls, and checks that the
contract and evidence blocks in the PR body describe this PR's route, head,
tree, base and scope. It never runs PR code and never writes to GitHub. Freshness,
overlap, approval and identity are listed as not evaluated; see the
[design](design/2026-11-02-maintainer-action.md) for the threat model.

## AI-contribution statements

Agents receive a `repository_policy` report on every `discover`, `inspect` and
`prepare`. It covers your CONTRIBUTING (including `.rst` and suffixed names such
as `CONTRIBUTING.en.md`), `AI_POLICY.md`, AGENTS.md/CLAUDE.md, PR templates, the
code of conduct and other policy files, plus your owner `.github` repository.
Lines that look like AI, agent or pull-request restrictions are quoted as hints.
The workflow requires agents to read the sources, record the result as the
contract prerequisite `ai-policy-review` (a refusal or anything unresolved
blocks implementation), stop when you refuse such contributions, treat
unreadable delegated policies as unresolved, and disclose agent assistance in
the PR.

Plain, explicit sentences in a Markdown, reStructuredText or text file in the
repository are easiest to find. Policies only on a website, wiki, image or PDF
are listed as not assessed. The legacy label policy `.agent-contrib.json` has no
opt-out field. Use a closed `.tipjar.json` for current invitation enforcement
and state refusals clearly in CONTRIBUTING.md for all clients.

## Practical guidance

Keep contribution policy and agent instructions consistent. State permitted
changes, required tests and how to report failures/skips. A portable reviewed
contract should include explicit allowed/prohibited paths, prerequisites,
acceptance criteria and evidence requirements. Avoid commands in issue text
that encourage agents to execute arbitrary downloaded code.

No GitHub App, webhook, hosted service or additional CI integration is required.
You may add repository-native checks later; this release supplies a passive
local verifier, not a trusted admission controller. Review actual diffs, logs
and provenance because evidence and reviewer identities are self-attested.

## Authorize one candidate without repository-wide opt-in

The v0.3.0 candidate adds an explicit schema 0.2 route for a same-repository task.
The human/host approves a reviewed contract and exact actions, while GitHub
independently confirms the personal credential's admin/maintain role. The issue
stays a candidate whether the opt-in policy is absent or simply lacks a matching
label. An unreadable or malformed policy still blocks.

Review the scope and retain your actual approval event and mandate hash outside
the worker. Do not let the worker fill an approval field on your behalf. Pending
final human sign-off need not prevent an authorized tested draft; it always
prevents final completion. See [the host handoff](host-authorization.md).
