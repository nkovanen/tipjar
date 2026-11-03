# Product status

Tipjar 0.3.0 is an **unreleased candidate**. Development continues in
[nkovanen/tipjar](https://github.com/nkovanen/tipjar). The website at
https://nkovanen.github.io/tipjar/ is planned and not live yet.

### Implemented

- Repository invitations: recognize the exact repository-scoped official README
  prefix and validate `.tipjar.json` manifest 0.1, inspect a pinned
  declaration with `jar`, and enforce welcome/closed/unknown states during
  discovery, preparation and live verification. A valid `closed` declaration is
  an implemented machine-readable opt-out. An absent jar grants no approval.
- `find`: verify one shared batch from two indexed public searches, five hits each;
  `--owner` narrows the search. Indexing can lag and no adoption is established.
- Issue discovery across named repositories, bounded `discover --limit` display,
  optional heuristic ranking and reports of ownership, overlap and prior fixes.
- Offline GitHub dependency candidates, bounded gift-session planning, public PR
  receipts, offline impact summaries and SVG gift cards.
- Task 0.3 external contributions from an immediate personal fork to a reviewed
  public issue, with separate implementation and exact-result publication gates.
  README/manifest provenance is bound through inventory format 4; old unpublished
  0.3 drafts require repreparation and fresh authorization.
- Task preparation, offline lint/scope checks, evidence skeletons, drift reports,
  PR-body generation and feedback observations.
- Schema 0.2 owner/maintainer authorization with separate implementation, draft
  and completion gates; host-context overlap dispositions and recognition after
  a host-authorized fast-forward draft update.
- Repository policy inventory and mandatory workflow review. Source approval,
  local execution and publication remain separate decisions. Explicit bans bind.
- G1 versioned output JSON Schemas, text summaries, rate-budget reports and an
  opt-in verified cache. Unknown schemas fail closed.
- Opt-in required CI checks at the exact completion head and a passive maintainer
  Action. The CLI's GitHub operations remain read-only.

### Partly implemented

- Authorization records are checked, but no native human/host mandate issuer
  ships. Evidence remains self-attested consistency data, not proof of consent
  or execution. See [host authorization](host-authorization.md).
- A jar invitation alone grants no outside-contributor upstream authority; use
  the explicit [external-tip route](external-tips.md). Existing fork experiments
  and owner/maintainer routes retain their documented boundaries.
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
