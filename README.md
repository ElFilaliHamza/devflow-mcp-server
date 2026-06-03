# DevFlow MCP Server

A project-aware AI sidekick for freelance developers. DevFlow gives Claude Code or any other LLM-powered tool like Codex or Cursor
a persistent memory of your projects, clients, coding standards, snippets, and
deployment commands — and a safe way to execute them.

## Features

- **Projects & clients** — onboard a project once, capture its README and
  `.env.example`, attach a client, switch active context any time.
- **Coding standards** — write a markdown style guide per client; check
  generated code against it before commit.
- **Knowledge base** — save snippets scoped globally, per project, or per
  client; save free-form insights from pairing sessions.
- **Deployment runbook** — register pre-approved commands (`make deploy-staging`,
  `docker compose up -d`, …) and run them with `dry_run` first. Subprocess
  calls use `shlex.split` with `shell=False` to prevent injection.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync
```

## Run

```bash
uv run python -m devflow_mcp
```

## Connect to Claude Code

Run this from the repository root (the directory that contains `pyproject.toml`):

```bash
claude mcp add devflow -- uv --project [devflow-absulute-path] run python -m   devflow_mcp
```

Verify with:

```bash
claude mcp list
```

The expected status is a green check (connected), not a red `failed`.

## Data location

State is persisted under `~/.devflow/`:

```
~/.devflow/
├── config.json    # projects, clients, style guides, runbook entries
└── snippets.db    # SQLite: snippets, insights
```

Override with the `DEVFLOW_HOME` environment variable:

```bash
DEVFLOW_HOME=/tmp/foo uv run python -m devflow_mcp
```

## Example session

1. `project.onboard(name="acme", path="~/code/acme", client="hf-corp")`
2. `client.set_styleguide(client="hf-corp", rules_markdown=...)`
3. `kb.save_snippet(title="Pre-commit", content="pre-commit install", project="acme")`
4. `runbook.add(project="acme", name="deploy-staging", command="make deploy-staging")`
5. `runbook.run(project="acme", name="deploy-staging", dry_run=true)` — review, then re-run with `dry_run=false`.

## Architecture

```
src/devflow_mcp/
├── __init__.py
├── __main__.py          # python -m devflow_mcp
├── paths.py             # ~/.devflow/ resolution + ensure_data_dir
├── config_store.py      # JSON config (projects, clients, runbook, style guides)
├── db.py                # SQLite (snippets, insights)
├── project_scanner.py   # README + .env.example readers
├── standards.py         # Regex-based rule checker
├── runbook.py           # command registration + subprocess execution
└── server.py            # FastMCP wiring (tools + resources)
```

## Development

```bash
uv sync
uv run pytest -q
```

## How it works

DevFlow gives Claude Code three things it doesn't have on its own: a
persistent memory of your projects, a way to enforce your clients' coding
rules, and a safe channel to run deployment commands. The tools are grouped
around these ideas.

### Projects and clients: keeping context straight

The first thing that breaks when you juggle freelance work is context. You
have four clients, each with two or three repos, and Claude Code has no idea
which repo you're in or whose rules apply. That's what devflow projects and clients tools
fix.

A **client** is the company you do work for. A **project** is one of their
repos. Style guides attach to clients, not projects, because `hf-corp`
wants the same Python style on every repo they pay you to touch. Use
`client.add` once per company. Use `project.onboard` once per repo. Onboard
reads the README and `.env.example` from the path you give it, so the next
time you open Claude Code in a fresh session, it can ask for a quick
summary instead of reading the whole file.

The **active project** is just whichever project is "in scope" right now.
If you only ever work on one project, you can ignore it. If you bounce
between repos, `project.set_current` is the way to say "we're working on
hf-web today." Most tools that take a project name will fall back to the
active one if you don't pass it.

### Coding standards: enforcing the way you actually work

Here's the real problem. You've settled into a way of working with
`hf-corp`: queries go through managers, business logic lives in service
classes, no raw SQL in views, models stay thin. It's the style you
enforce on every repo you touch for them, and you've explained it enough
times that you don't want to explain it again. But every time you onboard
a new project for hf-corp, or open Claude Code in a fresh session, you
end up re-asserting the same rules.

That's what `client.set_styleguide` is for. You write down the rules you
actually enforce for that client, in plain markdown, framed the way you'd
explain them to a junior: "queries belong in managers, not views," "no
business logic in views," "models stay thin." The server parses each line
into a regex and `standards.check` runs them against whatever code Claude
wrote.

The check is deliberately dumb. It's not a real linter, it doesn't
understand your codebase. It's a regex sweep that catches the things
you'd spot in a code review in five seconds: the `objects.filter(...)`
that should have been a manager method, the raw SQL that ended up in a
view, the untyped function you wrote too fast. The point isn't to
replace your real linter. The point is to offload the "wait, what
rules am I enforcing for this client right now?" decision from your
brain, every single time Claude generates code.

Set the guide for `hf-corp` once. Set the guide for `erp-corp` once,
with whatever different rules you enforce for them. Every new project
you onboard for either client inherits the right rules automatically,
because the guide is on the client, not the project.

### Knowledge base: notes that survive across sessions

Snippets and insights solve the same problem differently.

A **snippet** is "how to do X." "How to set up pre-commit." "How to run
migrations in this project." They have a title, content, optional tags, and
a scope. The scope is the part that matters: a snippet can be global,
project-scoped, or client-scoped. Save the hf-corp deploy command as
client-scoped, and the next time you onboard a project for hf-corp and
ask "how do I deploy this?", DevFlow finds it.

An **insight** is "I learned that X." "Always close the SQLite connection
in tests, or you get locked-file errors." "uvx is faster than uv tool run."
They're text-only and free-form. The point is that six months from now,
when you're about to make the same mistake, you can `kb.list_insights` and
see what past-you figured out.

Use `kb.save_snippet` when you find yourself writing the same code twice.
Use `kb.save_insight` when you finish a debugging session and don't want to
redo it.

### Runbook: deployment commands you can trust

The runbook is the most opinionated part of the system. The rule is:
nothing runs that wasn't registered first.

You add a command with `runbook.add`. It lives in your config file. When
you want to run it, you call `runbook.run` with `dry_run=true` first. The
server prints what it would do, no subprocess starts. You read the output,
confirm it's the command you meant, and call it again with `dry_run=false`.
Only then does anything actually execute.

Why this dance? Because deployment commands are the things you least want
to get wrong. A typo in a deploy command and you've shipped to the wrong
environment. The dry-run step is a few seconds of friction in exchange for
not having to roll back at 2am.

The server runs commands with `shell=False` after splitting them with
`shlex.split`, so injection isn't possible. If the command exits non-zero,
times out, or the binary is missing, you get a friendly error and the
result is saved to `runbook.status` so you can inspect what happened
without re-running.

### The flow in practice

A typical freelance dev day with DevFlow looks like this.

You open Claude Code in the hf-web repo. You ask it to use the DevFlow
tools. It calls `project.onboard` (or `project.set_current` if you've
onboarded before). Now everything is scoped to hf-web and hf-corp.

You ask Claude to write a function. It writes it. You ask it to check
that against the style guide. It calls `standards.check`, which loads
hf-corp's rules and returns violations. You fix them.

You're about to deploy. You ask what runbook entries are available. It
reads the `runbook://{project}/deploy` resource and shows the list. You
say run deploy-staging, dry run first. It calls `runbook.run` with
`dry_run=true`. You see the command. You say go. It runs for real.

Six months later, you're onboarding a second repo for hf-corp. You
`project.onboard` it. The style guide is already there. The deploy command
from the first repo isn't auto-shared (runbooks are per-project, by
design), but you can search snippets for "deploy-staging" and find the
hf-corp-scoped note you saved.

That's the system: persistent context, enforceable rules, repeatable
commands, and nothing magic. Every tool exists because the freelance dev
workflow has a real gap there, and the goal is to fill the gap without
adding a second one.

## License

MIT — see `LICENSE`.
