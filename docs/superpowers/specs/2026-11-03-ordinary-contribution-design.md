# Ordinary human-led contribution first

Status: design only; independent Terra approval is required before implementation.
Base: `d99751abc9f66c618a95e4975630377cc3c9e675`; implement on the final integrated badge-handoff head, not this old base.
Goal: help people contribute with their existing coding agent; present Tipjar's CLI/Skill and task0.3 verification as optional tools.

## Evidence and choice

- Landing step02 currently says “Use the CLI with your agent” and links only to installation ([source](https://github.com/nkovanen/tipjar/blob/d99751abc9f66c618a95e4975630377cc3c9e675/web/index.html#L98)).
- The current welcome detail offers `tipjar discover` without an ordinary contribution guide ([source](https://github.com/nkovanen/tipjar/blob/d99751abc9f66c618a95e4975630377cc3c9e675/web/leaderboard.js#L386)).
- Getting-started and tipping open with the advanced route; collector/form eligibility does not require its records ([collector](https://github.com/nkovanen/tipjar/blob/d99751abc9f66c618a95e4975630377cc3c9e675/tools/tipjar_board.py#L351)).
- Choose a short ordinary-first introduction and existing guide links; defer a wizard, new page, installer, executor and issuer.

## Copy and navigation contract

- Keep landing step02 title “Read the room.” Primary copy: “Use your own coding agent. Follow the project's contribution and AI rules. Review the plan and authorize work before it starts. Approve publication separately.”
- Primary link: “How to give a tip” → `https://github.com/nkovanen/tipjar/blob/main/docs/tipping.md#give-a-tip-with-your-existing-agent`.
- Retain the current `#install-from-source` URL as secondary “Optional: CLI & Skill”; no automatic installation.
- In `repoDetail`'s existing fresh welcome-only branch, show the same fixed guide link and: “You can use your own agent and the project's usual contribution process. Tipjar's CLI is optional.”
- Retain the existing discovery command and copy behavior, labeled “Optional CLI helper”; keep the existing policy/authorization notice.
- Closed, unknown, undeclared, absent, missing and expired observations receive no new invitation or work-start action.
- No new route parameters, repository interpolation, identity lookup, requests, clipboard payloads or stored state are introduced.

## Ordinary walkthrough and advanced route

- Add `## Give a tip with your existing agent` before the candidate CLI walkthrough in `docs/tipping.md`.
- Describe: choose an appropriate project/task; read contribution/AI rules and check overlapping work; agree permitted scope; review a plan; authorize execution; review/test the result; separately authorize publication; let maintainers decide.
- Ask maintainers before starting where their rules require it. Stop for bans, refusals, unresolved scope or permission; a welcome alone approves no task.
- After an eligible agent-assisted PR is actually merged, its author may use the existing merged-tip form for curator review. No acceptance, listing or score is promised.
- State plainly that this ordinary journey is not task0.3 machine verification. Existing project and user permissions remain necessary without a Tipjar contract.
- Label the existing CLI instructions “Optional: Tipjar CLI and task 0.3”; retain all commands, gates and explicit host requirements.
- Scope the current “bare tip this project needs a host” sentence to completing that optional task0.3 route. No native consent issuer ships; never invent host assertions, approval events or consent records.
- Put an ordinary-guide link first in `docs/getting-started.md`; label its existing installed CLI walkthrough as optional, preserving historical route requirements.
- Already adopted a task/Skill/protocol? Its constraints and gates remain binding. Do not relabel paused, refused, blocked or pending-authorization work as “ordinary” to continue; stop and resolve it through the adopted process.

## Bounded corrections to current guidance

- In `docs/tipping.md`, change its active output-schema claim from 3 to 4; task0.3/evidence0.2/external-context0.1/draft-payload0.1 remain unchanged.
- Replace the obsolete “separate incoming features” paragraph with current command availability; actual installed `--help` still decides version-specific availability.
- Rename Path two to “Explicitly choose a repository with no declared invitation”: current invitation2 `undeclared` includes a complete plain README without a welcome or absent invitation files, not merely missing JSON. Invalid/copied badges remain unknown; historical task0.1/0.2 manifest-only behavior stays separate.
- Correct only the current “new reports use output/3” sentence to output/4 in `docs/upgrading.md:130`, `docs/host-authorization.md:377`, `docs/architecture.md:100`, `docs/getting-started.md:268` (base line numbers).
- Authority: offline `instructions` returns output schema 4; `schema jar` returns `urn:agent-contrib:output:4:jar`; `agent_contribute/outputs.py:10` sets VERSION='4'. No historical resource/spec/plan rewrites.

## Ownership and fixed boundaries

- Future product edits: `web/index.html` step02 only; `web/leaderboard.js` welcome helper only; the five current docs named above.
- Badge-handoff owner ff7 confirmed those two UI sections are free; preserve its root banner, landing.js, hint helpers, lookup panel/router, identity/freshness/source logic and associated sections/tests.
- Separate maintainer design owns app.js/directory.html; suggestion-form PR13 is already integrated. Do not duplicate either flow.
- Existing submission form, eligibility, curator review, scoring, CLI/task/data/schema/gates and canonical Skill bytes are unchanged.
- This is no alternate authorization channel: no publishing, participant enrollment, GitHub writes, monetary claims or proof of verified AI use.

## Acceptance

A newcomer can find the ordinary route without installing anything; advanced users still find the real CLI prerequisites and gates.
A person with an adopted blocked task is told to stop, not switch routes; a non-welcome/expired detail cannot become a new invitation.
Current guidance agrees with output4 and invitation2; historical distinctions and all existing submission/permission requirements remain intact.
