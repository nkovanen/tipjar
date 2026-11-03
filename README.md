# Tipjar

Gift useful agent work to open-source projects, with human authorization at each step.

Tipjar is a Python CLI and a thin Skill for coding agents. It finds repository
invitations, ranks GitHub issues, reads project rules and overlapping pull
requests, and prepares task contracts for human review. The agent can then work
within the authorized scope. The CLI itself only reads GitHub; it never executes
contract commands or publishes contributions.

**Status:** 0.3.0 is an **unreleased candidate**. There is no 0.3.0 release tag
or PyPI release. The planned website is https://nkovanen.github.io/tipjar/;
it is **not live yet**. You can run the [directory demo locally](web/README.md).

## Install from source

Requires Python 3.10+, Git and [GitHub CLI](https://cli.github.com/).
With [pipx](https://pipx.pypa.io/latest/how-to/install-pipx.html):

```sh
pipx install 'git+https://github.com/nkovanen/tipjar.git@main'
tipjar --version       # 0.3.0
agent-contrib --version # same CLI
gh auth login
```

`main` moves as development continues. For reproducible installs, replace `main`
with a reviewed full commit SHA. See [installation](docs/installation.md) for
virtual environments, updates and agent host setup.

The distribution remains `agent-contrib`, the Python module remains
`agent_contribute`, and `tipjar` and `agent-contrib` invoke the same CLI. The
canonical Skill remains `agent-contribute`; existing scripts and schema
identifiers keep their names. The historical published release is
[Agent Contrib v0.2.0](https://github.com/nkovanen/agent-contrib/releases/tag/v0.2.0);
it has no `tipjar` command. See [upgrading](docs/upgrading.md).

Export the Skill for your agent (Codex shown; Claude Code uses
`$HOME/.claude/skills/agent-contribute`):

```sh
mkdir -p "$HOME/.agents/skills/agent-contribute"
agent-contrib skill --output "$HOME/.agents/skills/agent-contribute/SKILL.md"
```

The Skill uses the first `agent-contrib` on the agent host's PATH. Restart your
agent after installation, then say “Go help owner/repo.” Export refuses to
overwrite an existing Skill; [updates](docs/installation.md#compatibility-and-updates)
are deliberate.

## Find useful work

```sh
tipjar find --owner acme
tipjar jar acme/project
tipjar discover acme/project --signals --limit 10
tipjar inspect 'acme/project#12' --ownership
tipjar prepare 'acme/project#12' --output task.json
tipjar lint task.json
tipjar verify task.json
```

`find` verifies one batch of at most ten indexed public invitation candidates.
It is not an exhaustive directory, indexing can lag, and no adoption is
established. `jar` reads one repository's pinned invitation directly. `find` and
`discover --welcomed-only` select only `welcome` observations, subject to policy
review. Normal discovery and session planning can target an undeclared repository;
an absent jar grants no approval. Closed or unknown jars block readiness.
Explicit repository bans remain binding. [Find limits](docs/cli.md#find).

`discover` ranks issues; `--signals` re-ranks heuristically and never approves.
`--limit` bounds only the displayed list. `inspect` reports claims, linked PRs
and possible prior fixes. Preparation writes a draft contract; verification
reports blockers. A request to “help” stops for human authorization before work
starts. Publication requires its own authorization and passing draft gate;
nothing is automatically merged or released.

You can also shortlist GitHub projects from local dependency declarations with
`dependencies`, plan a bounded offline gift-work `session`, and record public
PR observations with `receipt` and `impact`. These reports grant no authority.

## External contributions and cards

For an outside contribution, use [task 0.3 external tips](docs/external-tips.md):
review the public issue and source/fork policies, authorize implementation in
an immediate personal fork, then separately approve the tested result and exact
upstream draft payload. Welcome and explicitly selected undeclared repositories
both require complete policy review. `verify --stage published` returns the
observed draft URL; a jar alone grants no authority. Evidence remains schema 0.2.

Create a local SVG from a recorded public PR observation with
`tipjar card receipt.json --output card.svg`, then share it manually. Cards retain
the receipt's observation time and state; they are not proof of consent or work.
See [receipts and cards](docs/receipts.md).

## Approval and authorization

An ordinary issue is a **candidate**. Labels such as `help wanted` do not permit
agent-generated work. A task is **policy-approved** only through an explicit
`.agent-contrib.json` policy and a configured label currently on the issue; the
CLI does not verify who applied it. Public issue events name an event actor, but
an outside contributor cannot use them to verify that actor's maintainer
authority. See [maintainer setup](docs/maintainers.md).

Schema 0.1 (the default) covers fork experiments and policy-approved work,
authorized by your explicit instruction. Schema 0.2 covers one candidate issue in
a repository you own or maintain: a host-issued mandate bound to the contract
hash, then separate `implementation`, `draft` and `completion` gates. Mandates are
an audit trail, not cryptographic consent ([host authorization](docs/host-authorization.md)).

## Safety model

- **Read-only GitHub.** The CLI runs only `gh api --method GET`. Locally it writes
  only files you name (never overwriting one) and, with `--cache`, its cache.
- **Untrusted text.** Issue text, repository instructions, contracts and evidence
  are data. The CLI never executes a contract's validation commands.
- **Fail closed.** Missing permissions, stale identities, unknown schema versions,
  unsafe checkout settings and incomplete reads block. An exit code is never
  authorization.
- **Separate decisions.** Source approval, permission to implement and permission
  to publish are separate records; one never implies another.
- **Nothing auto-published.** Publication is a draft PR, only after its own
  authorization. Nothing is merged, marked ready or released automatically.

## Commands

| Command | Purpose |
| --- | --- |
| `init`, `jar-check` | Create an explicit-state local invitation template; validate a local manifest offline |
| `dependencies` | Offline GitHub give-back candidates from local dependency declarations ([workflow](docs/dependencies.md)) |
| `session` | [Plan an offline gift-work shortlist](docs/planning-sessions.md) with explicit stopping caps |
| `jar` | Inspect one pinned root invitation; inspection only, no authority |
| `find` | Verify one public invitation batch (`--owner OWNER` optional) |
| `discover` | Rank issues of one repository, or 2–20 repositories |
| `inspect` | One issue: approval, instructions, exclusions, overlapping PRs |
| `prepare` | Write a draft contract (schema 0.1, or explicit 0.2/0.3 routes) |
| `lint` | Offline check of a contract against its schema and review rules |
| `verify` | Check a contract and evidence against live GitHub (0.2/0.3: `--stage`) |
| `authorization-request` | Unsigned 0.2 mandate request or 0.3 review view; grants nothing |
| `drift` | What changed since the contract was prepared |
| `scope-check`, `evidence init` | Offline scope check; evidence skeleton from observed Git facts |
| `pr-body`, `feedback` | PR description (publishes nothing); reviews and checks on a published PR |
| `receipt`, `impact` | Save public PR observations and summarize recorded impact offline ([receipts](docs/receipts.md)) |
| `card` | Create an offline SVG from a receipt; share manually |
| `audit`, `ownership` | Maintainer view of a repository; claims and possible prior fixes |
| `instructions`, `skill`, `schema` | Installed workflow, Skill export, output JSON Schemas |

Output is JSON; put `--format text` before the command for a summary. Exit codes
depend on the command and its gate; report-only observation failures can coexist
with exit 0. See the [command and exit-code index](docs/cli.md#command-index).

## Documentation

- [Getting started](docs/getting-started.md): a complete contribution walkthrough.
- [Installation](docs/installation.md) and [upgrading](docs/upgrading.md).
- [CLI reference](docs/cli.md) and [output schemas](docs/output-reference.md).
- [Maintainer setup](docs/maintainers.md) and [host authorization](docs/host-authorization.md).
- [Dependencies](docs/dependencies.md), [planning sessions](docs/planning-sessions.md)
  and [receipts](docs/receipts.md).
- [Architecture](docs/architecture.md), [security](SECURITY.md) and
  [compatibility notes](CHANGELOG.md#compatibility-notes).
- [Product map](docs/product-map.md), [development status](docs/development-status.md)
  and [historical plans](docs/archive/README.md).

Full regression coverage is Linux with Python 3.10–3.14. Windows/macOS CI covers
bounded host-context stdin and installed offline smoke checks; it does not
validate the full Git, cache or evidence workflows. Evidence is self-reported,
and no native host mandate issuer ships. See [current limits](docs/host-authorization.md).

## Development and provenance

Development continues in [nkovanen/tipjar](https://github.com/nkovanen/tipjar).
Read [CONTRIBUTING.md](CONTRIBUTING.md) for tests and package checks, and use
[private security reporting](https://github.com/nkovanen/tipjar/security/advisories/new)
for vulnerabilities.

Tipjar continues Agent Contrib with its Git history preserved. Historical release,
issue and PR links refer to the original `nkovanen/agent-contrib` repository.
[MIT](LICENSE); original attribution is retained in [NOTICE](NOTICE).
