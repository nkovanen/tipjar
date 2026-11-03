# Reviewed external tips (task 0.3)

A human may select a public issue in a welcoming repository or explicitly choose
an undeclared repository. An undeclared jar is absence of invitation, never
maintainer approval. Welcome is an invitation subject to every applicable rule.
Closed/unknown jars, known restrictions, incomplete policy and unresolved claims
block. The existing 0.1 label and 0.2 owner/maintainer routes keep their authority
requirements; nothing migrates an old contract.

Use one immediate public fork owned by the credential's personal user, one new
branch, the source default base and one new upstream draft. The host creates the
fork/checkout/branch using its own authority. Task preparation creates no permission:

```sh
agent-contrib prepare 'acme/project#12' --schema-version 0.3 --fork alice/project --head-ref tip-12 --output task.json
agent-contrib lint task.json
agent-contrib verify task.json --stage implementation --repo-dir CHECKOUT --host-context-stdin < implementation-context.json
agent-contrib evidence init task.json --repo-dir CHECKOUT --base SOURCE_SHA --output evidence.json
agent-contrib verify task.json --stage draft --repo-dir CHECKOUT --evidence evidence.json --publication-payload payload.json --host-context-stdin < publication-context.json
# Only the host performs the separately authorized exact push and upstream draft creation.
agent-contrib verify task.json --stage published --repo-dir CHECKOUT --evidence evidence.json --publication-payload payload.json --host-context-stdin < published-context.json
```

Keep task, contexts, evidence and payload outside the checkout. Review the task's
scope, criteria, prerequisites, validation argv and source-linked requirements
ledger before obtaining authority. Before implementation the checkout must be
clean at the source commit, on the exact new head ref with a matching fork remote
and no published branch. The CLI never executes validation argv; the host must
inspect scripts before running anything, then run all required checks without
filtering errors or accepting skips. Evidence initialization leaves results and
review pending; it writes unchanged evidence 0.2 bound to task 0.3.

The separate closed [external-context 0.1 schema](../agent_contribute/schemas/external-context/0.1.schema.json)
is explicit stdin/library input. It requires `implementation`, `policy_assessment`
and `policy_observations`; later add `publication_authorization`, and after host
publication add an untrusted `publication_claim`. The actual human/host issues
these assertions and retains originals outside worker control. A worker relays
records unchanged and must never generate consent. There is no consent issuer,
cryptographic proof of a human, or authenticated issuer-file system here.

Both authorizations bind the exact contract, personal actor, source **and fork**
format-3 inventories, canonical assessment hash, original policy-ledger bytes and
invitation basis. No-jar selection requires `undeclared_acknowledged: true` in
both; welcome uses false. This acknowledges “no declared agent invitation; I
choose to offer this policy-compliant draft, which maintainers may decline.”
Implementation actions are exactly `[implement]`; publication actions exactly
`[push_head, create_draft]`. Each event has a distinct ID/reference and a strict
positive interval no longer than 24 hours. Publication is a later decision after
all validations and independent review, covering exact evidence, review, commit,
tree, source base tip and parsed payload hashes. It authorizes no updates.

For **each** retained scanned-source and unassessed identity in both raw
inventories, supply one assessment row with quoted, digest-bound actual context.
Do not remove six ordinary references to make a no-jar inventory look empty.
Use false-positive/inapplicable only when actual referring context establishes
that disposition. Applicable contribution and release documents require actual
target evidence and the permitted constrained workflow in the ledger. Unreadable,
prohibited, ambiguous and unmet conditions remain blocked. The exact owner
`.github` lookup 404 may use `owner-lookup-404`, citing its stable
`inventory://REPOSITORY_ID/INVENTORY_SHA256` URI, inventory digest and canonical
hash of the `owner_lookup` object as its observation quote. A later failed lookup
is not that exception. Hiding limits and omitted sources cannot be assessed away.

The host rereads every applicable target before each live gate with its own
tools. Observations cover exactly those URI/revision pairs, match assessed
content hashes, succeed and are no older than 15 minutes when CLI reads finish.
They bind both inventories, the assessment and both authorization hashes without
a hash cycle. The CLI fetches no arbitrary external links. Changed or failed
rereads require policy re-review and new assessment/ledger/authorization bindings;
retain previous records for audit. Prose truth remains a host/reviewer judgment.

Retain the initial approved policy ledger unchanged as an evidence artifact,
including the canonical assessment hash. Add a separate final compliance artifact
with that hash and the final Git head. A tracked repository `.gitignore` rule can
keep the final review artifact outside the commit diff while inside the checkout;
local exclude settings cannot hide dirty files. Independent review must cover
these artifacts, the final diff and evidence, differ from the implementer and
follow final validations. Differing names alone prove no independence.

Prepare the exact [draft payload 0.1](../agent_contribute/schemas/draft-payload/0.1.schema.json)
with actual disclosure, evidence and source-template content: title, body,
`draft: true`, `maintainer_can_modify: false`. The CLI hashes exact parsed strings
without normalization. Review title/body safely before approval. Title is nonblank,
1–256 characters without C0/DEL; body is nonblank, at most 60,000 UTF-8 bytes.
Rerun the draft gate immediately before host actions and after push; the source tip
must equal the approved tip, and the remote head must be absent or exact.

The published gate reads all-state exact-head history in **both** repositories
across **all** base branches, plus live policy, ownership, checkout and evidence.
It recognizes only the numeric claimed upstream PR identity, author, draft state,
exact payload, fork head/tree and source base. Only its same numeric identity can
be exempted from duplicate/cross-reference findings; unrelated overlaps and
errors still block. The final detail GET must agree. Ordinary source advancement
is allowed at recognition when authorized and observed bases remain in history.
Expired authorization can recognize a draft created in its original interval;
it grants no new actions. A pass returns `next_action: return_draft` and the URL,
never acceptance, completion, ready, merge or release.

The host enforces single use and retains original creation head/payload. These
bounded, non-atomic observations cannot prove absence of earlier updates or
unlinked semantic duplicates. Organization/shared/non-immediate forks, adoption
of prior work, alternate bases, overlap waivers, updates/reopen, and required-CI
models are unsupported. `authorization-request` provides an unsigned implementation or exact draft review
view; it is never an external-context record or authorization. `drift` reports
source/inventory/jar differences and the current fork inventory hash (tasks store
no fork baseline). External policy targets still require manual host rereads.
`pr-body` writes a reviewable starting body with self-attested evidence limits and
pending host-context gates; it never publishes. `feedback` remains a generic
report and supplies no external lifecycle authority. See the
[tipping walkthrough](tipping.md) for these helper commands and human stops.
Use canonical JSON `external-tip-report/1` and output/3 schemas for automation.
