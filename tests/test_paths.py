from pathlib import Path

from devflow_mcp.paths import (
    CONFIG_PATH,
    DATA_DIR,
    DB_PATH,
    _resolve_data_dir,
    ensure_data_dir,
)


def test_data_dir_default_is_home_devflow(monkeypatch):
    """`_resolve_data_dir()` returns `~/.devflow` when no override is set.

    The bound `DATA_DIR` constant is computed once at import time, so we
    exercise the resolver function directly to keep this test deterministic
    regardless of the ambient `DEVFLOW_HOME` or the order of imports.
    """
    monkeypatch.delenv("DEVFLOW_HOME", raising=False)
    monkeypatch.setattr("devflow_mcp.paths._data_dir", None, raising=False)
    assert _resolve_data_dir() == Path.home() / ".devflow"


def test_config_path_is_under_data_dir():
    assert CONFIG_PATH.parent == DATA_DIR
    assert CONFIG_PATH.name == "config.json"


def test_db_path_is_under_data_dir():
    assert DB_PATH.parent == DATA_DIR
    assert DB_PATH.name == "snippets.db"


def test_ensure_data_dir_creates_directory(tmp_path, monkeypatch):
    from devflow_mcp import paths

    # pytest's `tmp_path` always exists, so use a non-existent subdir to prove
    # that `ensure_data_dir` is what creates the directory.
    target = tmp_path / "subdir"
    assert not target.exists()

    monkeypatch.setattr(paths, "_data_dir", target, raising=False)
    monkeypatch.setattr(paths, "DATA_DIR", target, raising=False)
    monkeypatch.setattr(paths, "CONFIG_PATH", target / "config.json", raising=False)
    monkeypatch.setattr(paths, "DB_PATH", target / "snippets.db", raising=False)

    ensure_data_dir()
    assert target.exists()
    assert target.is_dir()
