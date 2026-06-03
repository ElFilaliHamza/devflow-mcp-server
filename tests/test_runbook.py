from unittest.mock import patch

import pytest

from devflow_mcp import runbook
from devflow_mcp.config_store import load_config


def _add_entry(tmp_data_dir, project="acme", name="deploy-staging",
               command="make deploy-staging", description="Deploy to staging"):
    runbook.add_entry(project, name, command, description=description,
                      requires_approval=True)
    return load_config()


def test_add_entry_persists_to_config(tmp_data_dir):
    cfg = _add_entry(tmp_data_dir)
    assert "acme" in cfg["projects"]
    entry = cfg["projects"]["acme"]["runbook"]["deploy-staging"]
    assert entry["command"] == "make deploy-staging"
    assert entry["description"] == "Deploy to staging"
    assert entry["requires_approval"] is True


def test_list_entries_returns_sorted_names(tmp_data_dir):
    _add_entry(tmp_data_dir, name="deploy-prod", command="make deploy-prod")
    _add_entry(tmp_data_dir, name="deploy-staging", command="make deploy-staging")
    _add_entry(tmp_data_dir, name="lint", command="make lint")
    names = runbook.list_entries("acme")
    assert names == ["deploy-prod", "deploy-staging", "lint"]


def test_list_entries_unknown_project_returns_empty(tmp_data_dir):
    assert runbook.list_entries("ghost") == []


def test_run_dry_run_does_not_invoke_subprocess(tmp_data_dir):
    _add_entry(tmp_data_dir)
    with patch("devflow_mcp.runbook.subprocess.run") as mock_run:
        result = runbook.run_entry("acme", "deploy-staging", dry_run=True)
    assert "[DRY RUN]" in result
    assert "make deploy-staging" in result
    mock_run.assert_not_called()


def test_run_executes_via_shlex_split_with_shell_false(tmp_data_dir):
    _add_entry(tmp_data_dir, command="echo hello world")
    fake_result = type("R", (), {
        "returncode": 0, "stdout": "hello world\n", "stderr": ""
    })()
    with patch("devflow_mcp.runbook.subprocess.run", return_value=fake_result) as mock_run:
        result = runbook.run_entry("acme", "deploy-staging", dry_run=False)
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    # The command list is the first positional arg.
    assert args[0] == ["echo", "hello", "world"]
    # shell must be False to prevent injection.
    assert kwargs.get("shell", False) is False
    assert "Exit code: 0" in result
    assert "hello world" in result


def test_run_unknown_entry_raises(tmp_data_dir):
    _add_entry(tmp_data_dir)
    with pytest.raises(KeyError):
        runbook.run_entry("acme", "nonexistent", dry_run=False)


def test_run_unknown_project_raises(tmp_data_dir):
    with pytest.raises(KeyError):
        runbook.run_entry("ghost", "deploy", dry_run=False)


def test_status_returns_last_run_metadata(tmp_data_dir):
    _add_entry(tmp_data_dir)
    fake_result = type("R", (), {
        "returncode": 1, "stdout": "out", "stderr": "boom"
    })()
    with patch("devflow_mcp.runbook.subprocess.run", return_value=fake_result):
        runbook.run_entry("acme", "deploy-staging", dry_run=False)
    status = runbook.last_status("acme", "deploy-staging")
    assert status is not None
    assert status["returncode"] == 1
    assert status["stdout"] == "out"
    assert status["stderr"] == "boom"


def test_status_missing_returns_none(tmp_data_dir):
    _add_entry(tmp_data_dir)
    assert runbook.last_status("acme", "never-run") is None


def test_run_handles_missing_command(tmp_data_dir):
    """If the binary is missing, surface a friendly error instead of crashing."""
    _add_entry(tmp_data_dir, command="definitely-not-a-real-binary-xyz")
    with patch(
        "devflow_mcp.runbook.subprocess.run",
        side_effect=FileNotFoundError("definitely-not-a-real-binary-xyz not found"),
    ):
        result = runbook.run_entry("acme", "deploy-staging", dry_run=False)
    assert "Exit code: 127" in result
    assert "command not found" in result
    # Status was still persisted for follow-up inspection.
    status = runbook.last_status("acme", "deploy-staging")
    assert status is not None
    assert status["returncode"] == 127


def test_run_handles_timeout(tmp_data_dir):
    """If the command exceeds the timeout, return a friendly timeout message."""
    import subprocess as sp
    _add_entry(tmp_data_dir, command="sleep 999")
    with patch(
        "devflow_mcp.runbook.subprocess.run",
        side_effect=sp.TimeoutExpired(cmd=["sleep"], timeout=120),
    ):
        result = runbook.run_entry("acme", "deploy-staging", dry_run=False)
    assert "Exit code: 124" in result
    assert "timed out" in result


def test_load_config_returns_defaults_when_corrupted(tmp_data_dir):
    """A corrupted config.json is recovered gracefully."""
    from devflow_mcp import paths
    paths.CONFIG_PATH.write_text("{ this is not valid json", encoding="utf-8")
    cfg = runbook.load_config()
    assert cfg == {"projects": {}, "clients": {}, "current_project": None}


def test_save_config_is_atomic(tmp_data_dir):
    """save_config writes to a temp file then renames (no partial writes)."""
    from devflow_mcp import paths
    runbook.save_config({"projects": {"x": {"name": "x"}}, "clients": {}, "current_project": None})
    # No leftover .tmp file should exist after a successful save.
    tmp = paths.CONFIG_PATH.with_suffix(".json.tmp")
    assert not tmp.exists()
    assert paths.CONFIG_PATH.exists()
