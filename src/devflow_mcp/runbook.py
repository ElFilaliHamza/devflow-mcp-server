"""Per-project deployment runbook: register, list, and execute commands.

Commands are stored as strings (e.g. `make deploy-staging`) and executed
via `subprocess.run(..., shell=False)` after splitting with `shlex.split`.
Last-run results are persisted in the project entry of `config.json`.
"""

from __future__ import annotations

import shlex
import subprocess
from datetime import datetime, timezone
from typing import Any

from .config_store import load_config, save_config


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _project(config: dict[str, Any], project: str) -> dict[str, Any]:
    if project not in config["projects"]:
        raise KeyError(f"project not found: {project}")
    return config["projects"][project]


def add_entry(
    project: str,
    name: str,
    command: str,
    description: str = "",
    requires_approval: bool = True,
) -> None:
    """Register a runbook command on a project. Creates the project if absent."""
    config = load_config()
    if project not in config["projects"]:
        config["projects"][project] = {
            "name": project,
            "path": "",
            "client": "",
            "stack": "",
            "description": "",
            "runbook": {},
            "last_runs": {},
        }
    proj = config["projects"][project]
    proj.setdefault("runbook", {})
    proj["runbook"][name] = {
        "command": command,
        "description": description,
        "requires_approval": requires_approval,
    }
    proj.setdefault("last_runs", {})
    save_config(config)


def list_entries(project: str) -> list[str]:
    config = load_config()
    if project not in config["projects"]:
        return []
    return sorted((config["projects"][project].get("runbook") or {}).keys())


def run_entry(project: str, name: str, dry_run: bool = False) -> str:
    config = load_config()
    proj = _project(config, project)
    runbook_map = proj.get("runbook") or {}
    if name not in runbook_map:
        raise KeyError(f"runbook entry not found: {project}/{name}")
    command_str = runbook_map[name]["command"]
    if dry_run:
        return f"[DRY RUN] Would execute: {command_str}"

    cmd_list = shlex.split(command_str)
    try:
        result = subprocess.run(  # noqa: S603 — shell=False by design
            cmd_list,
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
        )
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr
        error_msg = ""
    except FileNotFoundError as exc:
        returncode = 127
        stdout = ""
        stderr = ""
        error_msg = f"command not found: {exc}"
    except subprocess.TimeoutExpired as exc:
        returncode = 124
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        error_msg = f"command timed out after {exc.timeout} seconds"
    except OSError as exc:
        returncode = 126
        stdout = ""
        stderr = ""
        error_msg = f"OS error running command: {exc}"

    proj.setdefault("last_runs", {})[name] = {
        "returncode": returncode,
        "stdout": stdout,
        "stderr": stderr,
        "ran_at": _now_iso(),
        "command": command_str,
    }
    save_config(config)

    header = f"Exit code: {returncode}"
    if error_msg:
        header += f" ({error_msg})"
    return (
        f"{header}\n"
        f"STDOUT:\n{stdout}\n"
        f"STDERR:\n{stderr}"
    )


def last_status(project: str, name: str) -> dict[str, Any] | None:
    config = load_config()
    if project not in config["projects"]:
        return None
    runs = config["projects"][project].get("last_runs") or {}
    return runs.get(name)
