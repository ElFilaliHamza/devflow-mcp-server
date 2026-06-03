"""DevFlow FastMCP server.

Run with: `python -m devflow_mcp`
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import db as dbmod
from .config_store import load_config, save_config
from .project_scanner import scan_env_template, scan_readme, summarize_readme

mcp = FastMCP("DevFlow")


# ---------------------------------------------------------------------------
# Project tools
# ---------------------------------------------------------------------------

@mcp.tool()
def project_onboard(
    name: str,
    path: str,
    client: str,
    description: str = "",
    stack: str = "",
) -> str:
    """Onboard a project: scan its directory, store metadata under `~/.devflow/config.json`."""
    project_path = Path(path).expanduser()
    readme = scan_readme(project_path)
    env_template = scan_env_template(project_path)

    config = load_config()
    config["projects"][name] = {
        "name": name,
        "path": str(project_path),
        "client": client,
        "description": description,
        "stack": stack,
        "readme_summary": summarize_readme(readme),
        "env_template": env_template,
        "runbook": {},
        "last_runs": {},
    }
    # Auto-register the client so style guides can be attached later.
    config["clients"].setdefault(
        client, {"name": client, "website": "", "notes": ""}
    )
    if config.get("current_project") is None:
        config["current_project"] = name
    save_config(config)

    return (
        f"Onboarded project '{name}' (client={client}, stack={stack or 'unspecified'}). "
        f"Captured {len(readme)} chars of README and {len(env_template)} chars of env template."
    )


@mcp.tool()
def project_list() -> str:
    """List all onboarded projects, one per line, prefixed with the active project marker."""
    config = load_config()
    projects = config.get("projects") or {}
    if not projects:
        return "No projects onboarded yet."
    current = config.get("current_project")
    lines = []
    for name in sorted(projects.keys()):
        marker = "*" if name == current else " "
        client = projects[name].get("client", "")
        lines.append(f"{marker} {name} (client={client})")
    return "\n".join(lines)


@mcp.tool()
def project_set_current(name: str) -> str:
    """Mark a project as the active context for subsequent operations."""
    config = load_config()
    if name not in config["projects"]:
        raise KeyError(f"project not found: {name}")
    config["current_project"] = name
    save_config(config)
    return f"Active project is now '{name}'."


@mcp.resource("project://{name}/readme")
def project_readme_resource(name: str) -> str:
    """Return the cached README summary for a project."""
    config = load_config()
    proj = config["projects"].get(name)
    if proj is None:
        return f"Project not found: {name}"
    summary = proj.get("readme_summary") or ""
    if not summary:
        return f"README not found for project '{name}'."
    return summary


@mcp.resource("project://current")
def current_project_resource() -> str:
    """Return a short summary of the currently active project."""
    config = load_config()
    name = config.get("current_project")
    if not name:
        return "No active project. Use project.set_current(name) to choose one."
    proj = config["projects"].get(name)
    if proj is None:
        return f"Active project '{name}' is missing from config."
    return (
        f"Active project: {name}\n"
        f"Client: {proj.get('client', '')}\n"
        f"Stack: {proj.get('stack', '') or 'unspecified'}\n"
        f"Description: {proj.get('description', '')}\n"
        f"Path: {proj.get('path', '')}"
    )


# ---------------------------------------------------------------------------
# Client tools
# ---------------------------------------------------------------------------

@mcp.tool()
def client_add(name: str, website: str = "", notes: str = "") -> str:
    """Register a client."""
    config = load_config()
    config["clients"][name] = {"name": name, "website": website, "notes": notes}
    save_config(config)
    return f"Registered client '{name}'."


@mcp.tool()
def client_list() -> str:
    """List all registered clients."""
    config = load_config()
    clients = config.get("clients") or {}
    if not clients:
        return "No clients registered yet."
    return "\n".join(
        f"- {name} ({client.get('website', '')})" for name, client in sorted(clients.items())
    )



# ---------------------------------------------------------------------------
# Style guides & standards
# ---------------------------------------------------------------------------

@mcp.tool()
def client_set_styleguide(client: str, rules_markdown: str) -> str:
    """Attach or replace the markdown style guide for a client."""
    config = load_config()
    if client not in config["clients"]:
        config["clients"][client] = {"name": client, "website": "", "notes": ""}
    config["clients"][client]["styleguide"] = rules_markdown
    save_config(config)
    return f"Stored style guide for client '{client}' ({len(rules_markdown)} chars)."


@mcp.tool()
def client_get_styleguide(client: str) -> str:
    """Return the style guide markdown for a client, or a 'missing' message."""
    config = load_config()
    entry = config["clients"].get(client)
    if not entry or not entry.get("styleguide"):
        return f"No style guide recorded for client '{client}'."
    return entry["styleguide"]


@mcp.resource("standards://{client}/rules")
def standards_rules_resource(client: str) -> str:
    """Return the style guide markdown for a client."""
    return client_get_styleguide(client)


@mcp.tool()
def standards_check(name: str | None, code: str) -> str:
    """Check `code` against the style guide of the current (or named) project.

    `name` is the project name. If omitted, the currently active project is used.
    The project's client must have a style guide recorded.
    """
    from .standards import RegexRuleChecker

    config = load_config()
    project_name = name or config.get("current_project")
    if not project_name or project_name not in config["projects"]:
        return f"No project context (looked for '{project_name}'). Set one with project.set_current."
    proj = config["projects"][project_name]
    client = proj.get("client")
    if not client:
        return f"Project '{project_name}' has no client; cannot look up style guide."
    client_entry = config["clients"].get(client) or {}
    rules_md = client_entry.get("styleguide")
    if not rules_md:
        return f"No style guide recorded for client '{client}'."

    checker = RegexRuleChecker.from_markdown(rules_md)
    violations = checker.check(code)
    if not violations:
        return f"No violations of {client}'s style guide."
    lines = [f"{len(violations)} violation(s) of {client}'s style guide:"]
    for v in violations:
        lines.append(f"- line {v.line}: '{v.match}' (rule: {v.pattern})")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

@mcp.tool()
def kb_save_snippet(
    title: str,
    content: str,
    tags: str = "",
    project: str = "",
    client: str = "",
) -> str:
    """Save a code snippet. Optionally scope it to a project and/or client."""
    dbmod.init_db()
    snippet_id = dbmod.insert_snippet(
        title=title, content=content, tags=tags, project=project, client=client
    )
    return f"Saved snippet #{snippet_id}: '{title}'."


@mcp.tool()
def kb_search_snippets(query: str) -> str:
    """Fuzzy substring search over snippet title, content, and tags."""
    dbmod.init_db()
    rows = dbmod.search_snippets(query)
    if not rows:
        return f"No snippets matched '{query}'."
    out = [f"{len(rows)} snippet(s) matched '{query}':"]
    for r in rows:
        scope_parts = [p for p in (r["project"], r["client"]) if p]
        scope = f" [{' / '.join(scope_parts)}]" if scope_parts else ""
        tags = f" (tags: {r['tags']})" if r["tags"] else ""
        out.append(
            f"- #{r['id']} {r['title']}{tags}{scope}\n  {r['content']}"
        )
    return "\n".join(out)


@mcp.tool()
def kb_save_insight(text: str, source: str = "") -> str:
    """Save a free-form lesson learned."""
    dbmod.init_db()
    insight_id = dbmod.insert_insight(text=text, source=source)
    return f"Saved insight #{insight_id}."


@mcp.tool()
def kb_list_insights() -> str:
    """Return all saved insights, newest first."""
    dbmod.init_db()
    rows = dbmod.fetch_all_insights()
    if not rows:
        return "No insights recorded yet."
    return "\n".join(
        f"- #{r['id']} {r['text']} (source: {r['source'] or 'unspecified'})"
        for r in rows
    )


@mcp.resource("kb://snippets/{tag}")
def kb_snippets_resource(tag: str) -> str:
    """Return all snippets whose tags contain `tag` (case-insensitive)."""
    dbmod.init_db()
    all_snippets = dbmod.fetch_all_snippets()
    matched = [
        s for s in all_snippets
        if tag.lower() in (s.get("tags") or "").lower()
    ]
    if not matched:
        return f"No snippets tagged '{tag}'."
    return "\n".join(
        f"- #{s['id']} {s['title']}\n  {s['content']}" for s in matched
    )


@mcp.resource("kb://insights")
def kb_insights_resource() -> str:
    """Return all insights as a resource."""
    return kb_list_insights()


# ---------------------------------------------------------------------------
# Runbook
# ---------------------------------------------------------------------------

from . import runbook as _runbook  # noqa: E402  (placed here to keep grouped with tools)


@mcp.tool()
def runbook_add(
    project: str,
    name: str,
    command: str,
    description: str = "",
    requires_approval: bool = True,
) -> str:
    """Register a runbook command on a project."""
    _runbook.add_entry(
        project=project,
        name=name,
        command=command,
        description=description,
        requires_approval=requires_approval,
    )
    return f"Added runbook entry '{name}' to project '{project}'."


@mcp.tool()
def runbook_list(project: str) -> str:
    """List the names of runbook entries on a project."""
    names = _runbook.list_entries(project)
    if not names:
        return f"Project '{project}' has no runbook entries."
    return "\n".join(f"- {n}" for n in names)


@mcp.tool()
def runbook_run(project: str, name: str, dry_run: bool = False) -> str:
    """Execute a runbook command, or describe what would run when `dry_run=True`."""
    return _runbook.run_entry(project=project, name=name, dry_run=dry_run)


@mcp.tool()
def runbook_status(project: str, name: str) -> str:
    """Return the most recent run result for an entry, or 'never run'."""
    status = _runbook.last_status(project, name)
    if status is None:
        return f"'{name}' has not been run yet for project '{project}'."
    return (
        f"Last run at {status['ran_at']} (exit {status['returncode']}):\n"
        f"Command: {status['command']}\n"
        f"STDOUT: {status['stdout']}\n"
        f"STDERR: {status['stderr']}"
    )


@mcp.resource("runbook://{project}/deploy")
def runbook_resource(project: str) -> str:
    """Human-readable summary of a project's runbook."""
    config = load_config()
    proj = config["projects"].get(project)
    if proj is None:
        return f"Project not found: {project}"
    entries = proj.get("runbook") or {}
    if not entries:
        return f"Project '{project}' has no runbook entries."
    lines = [f"Runbook for project '{project}':"]
    for name in sorted(entries.keys()):
        e = entries[name]
        lines.append(
            f"- {name}: `{e['command']}` "
            f"({'requires approval' if e.get('requires_approval') else 'no approval'}) "
            f"— {e.get('description', '')}"
        )
    return "\n".join(lines)


def main() -> None:
    mcp.run(transport="stdio")
