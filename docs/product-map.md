# Product status

Tipjar 0.3.0 is an **unreleased candidate**. Development continues in
[nkovanen/tipjar](https://github.com/nkovanen/tipjar). The website at
https://nkovanen.github.io/tipjar/ is planned and not live yet.

### Implemented

- Repository invitations: validate `.tipjar.json` manifest 0.1, inspect a pinned
  declaration with `jar`, and enforce welcome/closed/unknown states during
  discovery, preparation and live verification. A valid `closed` declaration is
  an implemented machine-readable opt-out. An absent jar grants no approval.
- `find`: verify one indexed public batch of at most ten invitation candidates;
  `--owner` narrows the search. Indexing can lag and no adoption is established.
- Issue discovery across named repositories, bounded `discover --limit` display,
  optional heuristic ranking and reports of ownership, overlap and prior fixes.
- Offline GitHub dependency candidates, bounded gift-session planning, public PR
  receipts, offline impact summaries and local SVG `card` exports for manual sharing.
- Task preparation, offline lint/scope checks, evidence skeletons, drift reports,
  PR-body generation and feedback observations.
- Schema 0.2 owner/maintainer authorization with separate implementation, draft
  and completion gates; host-context overlap dispositions and recognition after
  a host-authorized fast-forward draft update.
- Task schema 0.3 external tips from an immediate personal fork to a selected
  public upstream issue, with separate implementation and exact-result draft
  publication assertions. Welcome and explicitly selected undeclared sources
  require source/fork policy accounting. See [external tips](external-tips.md).
- Repository policy inventory and mandatory workflow review. Source approval,
  local execution and publication remain separate decisions. Explicit bans bind.
- G1 versioned output JSON Schemas: output/3 covers all 25 commands and reports,
  preserving output/1 and output/2. Text summaries, rate-budget reports and an
  opt-in verified cache. Unknown schemas fail closed.
- Opt-in required CI checks at the exact completion head and a passive maintainer
  Action. The CLI's GitHub operations remain read-only.

### Partly implemented

- Authorization records are checked, but no native human/host mandate issuer
  ships. Evidence remains self-attested consistency data, not proof of consent
  or execution. See [host authorization](host-authorization.md).
- External tips require actual human/host assertions; a jar alone grants no
  authority. Evidence remains schema 0.2. Existing 0.1/0.2 routes retain their
  boundaries; external delivery stops at the observed upstream draft.
- Draft updates are recognized after the authorized push; pre-push readiness,
  force-push adoption and reopening are unsupported.
- Policy hints, ownership, possible prior fixes and signature observations are
  reports, not approval. Public issue events name an actor. This is a
  documented limitation; labeling-actor authority cannot be verified from public REST data.
- The maintainer Action does not perform live approval, freshness, identity or
  overlap checks. Full Git/cache/evidence portability is validated on Linux;
  Windows/macOS CI covers only bounded host input and installed offline smoke checks.

## Development and history

Use the [CLI reference](cli.md) for exact behavior, [architecture](architecture.md)
for implementation, [security](../SECURITY.md) for trust boundaries and
[releasing](releasing.md) for release gates. No release, publication or deployment
is authorized by this status page.

The former issue grid is preserved in the
[Agent Contrib product map at ae206ce](https://github.com/nkovanen/agent-contrib/blob/ae206ce0ef079cd369dda0803a4374ca177516bd/docs/product-map.md).
Its issue and PR numbers belong to `nkovanen/agent-contrib`. Completed
[implementation plans](archive/README.md) are linked separately; active security
and compatibility specifications remain in this tree.
