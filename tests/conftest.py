"""Shared pytest fixtures for the DevFlow test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from devflow_mcp import paths


@pytest.fixture(autouse=True)
def _isolate_devflow_home(monkeypatch):
    """Ensure `DEVFLOW_HOME` is unset for every test so default-path tests
    are deterministic regardless of the developer's environment."""
    monkeypatch.delenv("DEVFLOW_HOME", raising=False)


@pytest.fixture
def tmp_data_dir(tmp_path, monkeypatch) -> Path:
    """Redirect all of `devflow_mcp.paths` to a fresh temp directory.

    The data directory is created before the test body runs (via
    `paths.ensure_data_dir()`), so tests may safely write into it.
    """
    monkeypatch.setattr(paths, "_data_dir", tmp_path, raising=False)
    monkeypatch.setattr(paths, "DATA_DIR", tmp_path, raising=False)
    monkeypatch.setattr(paths, "CONFIG_PATH", tmp_path / "config.json", raising=False)
    monkeypatch.setattr(paths, "DB_PATH", tmp_path / "snippets.db", raising=False)
    paths.ensure_data_dir()
    return tmp_path
