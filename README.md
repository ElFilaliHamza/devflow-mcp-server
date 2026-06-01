# DevFlow MCP Server

A project-aware AI sidekick for freelance developers. Manages projects, clients,
coding standards, code snippets, and safe deployment runbooks — all from inside
Claude Code.

## Why DevFlow?

Freelancers and solo developers juggle dozens of small projects, each with its
own client conventions, deployment quirks, and hard-won snippets of knowledge.
DevFlow keeps that context where your AI already lives: in the chat.

## Install

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11+.

```bash
uv sync
```

## Run (development)

```bash
uv run python -m devflow_mcp
```

## Connect to Claude Code

```bash
claude mcp add devflow -- uv run python -m devflow_mcp
```

## Data location

DevFlow stores state under `~/.devflow/` (`config.json` + `snippets.db`).
Override `DEVFLOW_HOME` to relocate it.

## License

MIT — see `LICENSE`.
