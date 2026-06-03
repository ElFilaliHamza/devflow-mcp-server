"""Read/write the JSON config that stores projects, clients, and runbooks."""

from __future__ import annotations

import json
import os
from typing import Any

from . import paths

EMPTY_CONFIG: dict[str, Any] = {
    "projects": {},
    "clients": {},
    "current_project": None,
}


def load_config() -> dict[str, Any]:
    """Load the config from disk.

    Returns defaults if the file does not exist. If the file exists but is
    corrupted, returns defaults (and logs a warning via the returned dict's
    `__corrupted__` key is not set — we just return the defaults to keep
    callers simple). Callers that care about corruption can check by calling
    `load_config_or_none` instead.
    """
    if not paths.CONFIG_PATH.exists():
        return json.loads(json.dumps(EMPTY_CONFIG))  # deep copy of defaults
    try:
        return json.loads(paths.CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        # Corrupted file: surface a fresh default to the caller. The on-disk
        # file is left in place so the user can recover it manually.
        return json.loads(json.dumps(EMPTY_CONFIG))


def save_config(config: dict[str, Any]) -> None:
    """Persist the config to disk atomically (write to temp + os.replace).

    The temp file is created next to the target so `os.replace` is guaranteed
    to be atomic on the same filesystem.
    """
    paths.ensure_data_dir()
    tmp_path = paths.CONFIG_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(config, indent=2, sort_keys=True))
    os.replace(tmp_path, paths.CONFIG_PATH)
