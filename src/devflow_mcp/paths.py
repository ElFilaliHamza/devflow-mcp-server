"""Filesystem layout for DevFlow.

All persistent state lives under a single data directory, defaulting to
`~/.devflow/`. Tests override the data directory via the module-level
`_data_dir` (see `conftest.py`).
"""

from __future__ import annotations

import os
from pathlib import Path

# Module-level indirection so tests can monkeypatch a single attribute.
_data_dir: Path | None = None


def _resolve_data_dir() -> Path:
    """Resolve the data directory.

    Precedence:
    1. `_data_dir` module attribute (tests set this).
    2. `DEVFLOW_HOME` environment variable.
    3. `Path.home() / ".devflow"`.
    """
    if _data_dir is not None:
        return _data_dir
    env = os.environ.get("DEVFLOW_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / ".devflow").resolve()


def _make_paths() -> tuple[Path, Path, Path]:
    root = _resolve_data_dir()
    return root, root / "config.json", root / "snippets.db"


DATA_DIR, CONFIG_PATH, DB_PATH = _make_paths()


def ensure_data_dir() -> Path:
    """Create the data directory if it does not exist. Returns the path."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
