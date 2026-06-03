from textwrap import dedent

from devflow_mcp.project_scanner import (
    scan_env_template,
    scan_readme,
    summarize_readme,
)


def test_scan_readme_returns_contents(tmp_path):
    (tmp_path / "README.md").write_text("# Hello\n\nWelcome.\n", encoding="utf-8")
    result = scan_readme(tmp_path)
    assert result == "# Hello\n\nWelcome.\n"


def test_scan_readme_missing_returns_empty(tmp_path):
    assert scan_readme(tmp_path) == ""


def test_scan_env_template_returns_contents(tmp_path):
    (tmp_path / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
    assert scan_env_template(tmp_path) == "API_KEY=\n"


def test_scan_env_template_missing_returns_empty(tmp_path):
    assert scan_env_template(tmp_path) == ""


def test_summarize_readme_truncates_long_text():
    body = "# Title\n\n" + ("lorem ipsum dolor sit amet " * 200)
    summary = summarize_readme(body, max_chars=80)
    assert summary.startswith("# Title")
    assert len(summary) <= 80


def test_summarize_readme_short_unchanged():
    assert summarize_readme("short", max_chars=80) == "short"
