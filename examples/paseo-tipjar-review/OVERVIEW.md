# Tipjar request review

Inspect and copy an unsigned external Tipjar request in a Paseo screen. This source-only
example targets Paseo app and daemon 0.15.0. It is a review aid, not a consent issuer.

Paste the complete JSON emitted by `authorization-request` for task 0.3. Inspect shows
the entire request, its reported bindings, both policy inventories and every diagnostic.
Control and directional characters are escaped in the preview. Copy writes the original
unsigned input to the current device's clipboard and reports failures. It never copies
an authorization record or adds approval fields. Clipboard contents can contain private
repository data; copying is an explicit user action.

The view is a potentially stale uploaded snapshot. This helper format carries no policy
observation timestamps, complete contract, evidence, assessment text, ledger or PR payload;
their reported hashes do not verify their contents. Freshness stays unknown and blocks
action. Read those materials separately and run fresh CLI verification before any action.
Editing the input clears the old view; Inspect builds a replacement. No live refresh occurs.

Time and task budgets are proposals only: one task, initially 60 minutes, at most 480.
The proposed deadline uses the client clock at inspection. Nothing enforces these values
or includes them in copied JSON. Nothing in this screen authorizes work or publication.

All parsing happens in the app. Input is bounded to 1 MiB UTF-8 and depth 64. Numeric
tokens must be integers in ±9,007,199,254,740,991; decimals, exponents and negative zero
are refused rather than silently normalized. Unknown request versions and extra fields
are refused. The displayed digest hashes the canonical unsigned request, not its contract.

The example has no server entry, RPC, file access, external retrieval, worker dispatch,
validation execution or GitHub writes. Pasted data is held only in component memory and
is cleared when the screen unmounts or the selected host changes. Paseo plugins generally
run as trusted code; this viewer does not establish a human-event or storage trust boundary.
Native app and real clipboard trials have not been performed; #23 remains open.
