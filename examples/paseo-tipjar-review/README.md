# Source-only Paseo review example

See [OVERVIEW.md](OVERVIEW.md) for the user flow and limitations. This example is optional;
the Python CLI/library and canonical Skill have no dependency on Paseo or this directory.
The current Tipjar CLI supports task schemas 0.1 and 0.2; it does not ship the candidate
task 0.3 external helper that produced these fixtures. This example adds no CLI/schema
support or native consent issuer and is excluded from both the wheel and source archive.

The inspected input is a potentially stale uploaded snapshot, with no policy observation
timestamps or complete contract contents, evidence, assessment text, ledger or PR payload.
Reported hashes cannot verify those missing contents. Freshness remains unknown and blocks
action: review the materials separately and obtain fresh CLI verification before any action.
Editing input clears the inspected view; Inspect replaces it without a live refresh.

## Reproduce development checks

Use Node.js 22.12+ (or Node 24+) and npm, with Python 3 available for **test-only** hash parity:

```sh
cd examples/paseo-tipjar-review
npm ci --ignore-scripts --no-audit --no-fund
npm test
npm run typecheck
npm run bundle-check
```

These commands install development dependencies into this directory, not a Paseo plugin.
No Paseo install/enable/reload, config modification or live app trial is part of the checks.
Runtime imports are React/React Native and the host clipboard API, plus bundled pure JS
schema validation/hashing. Python is never called by the example at runtime.

## Pinned primary-source contracts

- Published [`@getpaseo/plugin` 0.15.0](https://www.npmjs.com/package/@getpaseo/plugin/v/0.15.0),
  [`client/contracts.ts`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/plugin/src/client/contracts.ts):
  `addScreen`, `addSidebarHeaderItem`, screen host/theme/layout props and registration cleanup.
- [`client/ui.ts`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/plugin/src/client/ui.ts)
  exports `SidebarRow` and `copyText`; app clipboard implementations
  [`native`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/app/src/plugins/react-native/clipboard.ts)
  and [`web`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/app/src/plugins/react-native/clipboard.web.ts)
  provide an awaited operation that can reject. No fallback claims success.
- [`operation-permissions.ts`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/server/src/server/authorization/operation-permissions.ts)
  maps plugin RPC to `daemon.manage`; [`session.ts`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/server/src/server/session.ts)
  forwards plugin ID/method/input. This authenticates neither a gesture nor a human.
  The example avoids that path entirely; it registers no server or approval RPC.
- [`compiler-build.ts`](https://github.com/getpaseo/paseo/blob/v0.15.0/packages/server/src/server/plugins/compiler-build.ts)
  defines client/shared import boundaries. No root code modules besides `index.client.tsx`,
  no DOM API/library in production TypeScript, no Node runtime imports.
- `shared/authorization-request.schema.json` is copied **verbatim** from
  `agent_contribute/schemas/output/3/authorization-request.schema.json` at
  `cb5570443011189fc05960b633a11e36d01c6031`. The viewer additionally accepts only
  `agent-contrib/external-authorization-request`, request 0.1, `issued: false`,
  `ready_for_issuance: false`, with matching contract-hash bindings and stage actions.
  This is the existing unsigned format, not a new authority envelope. Do not replace it
  silently when a future helper changes; review the new source/schema and tests first.

The two request fixtures are synthetic outputs of that candidate's `authrequest.build`
using `tests.test_external_tip_e2e.ExternalTipEndToEndTests` with fake GitHub and temporary
Git repositories. They contain no retained human decisions or live evidence. The full
schema retains legacy definitions solely for faithful source provenance; legacy requests
are explicitly refused by this viewer.

## Verification limits

Tests use real React Native Web primitives in jsdom at compact/wide layouts, including
dark theme colors. They exercise parsing, unsupported authority input, safe numeric bounds,
Python canonicalization/hash parity in that domain, control escaping, exact original copy,
clipboard rejection and replacement races. Clipboard IO alone is injected in component tests.
Source typechecks against the published SDK and real React Native types; it is not a claim
that a native app or daemon loaded the plugin. Controller-owned independent implementation
review, PR/CI, and any separately authorized native device trial remain outstanding.
