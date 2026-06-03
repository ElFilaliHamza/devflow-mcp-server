import json
from unittest.mock import patch

import pytest

from devflow_mcp import server
from devflow_mcp import db as dbmod
from devflow_mcp.config_store import load_config


# --- Style guides ----------------------------------------------------------

RULES = "# Acme rules\n- No console.log: forbid `console\\.log`\n"


def test_client_set_styleguide_persists(tmp_data_dir):
    server.client_add(name="acme-corp")
    server.client_set_styleguide(client="acme-corp", rules_markdown=RULES)
    cfg = load_config()
    assert cfg["clients"]["acme-corp"]["styleguide"] == RULES


def test_client_get_styleguide_returns_markdown(tmp_data_dir):
    server.client_add(name="acme-corp")
    server.client_set_styleguide(client="acme-corp", rules_markdown=RULES)
    text = server.client_get_styleguide("acme-corp")
    assert "No console.log" in text


def test_standards_rules_resource(tmp_data_dir):
    server.client_add(name="acme-corp")
    server.client_set_styleguide(client="acme-corp", rules_markdown=RULES)
    text = server.standards_rules_resource("acme-corp")
    assert "No console.log" in text


def test_standards_check_uses_project_client(tmp_data_dir):
    server.client_add(name="acme-corp")
    server.client_set_styleguide(client="acme-corp", rules_markdown=RULES)
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.project_set_current("acme")
    text = server.standards_check(name=None, code="console.log('hi');")
    assert "console.log" in text
    assert "1" in text  # line number


def test_standards_check_unknown_client_returns_message(tmp_data_dir):
    server.client_add(name="acme-corp")
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.project_set_current("acme")
    text = server.standards_check(name=None, code="anything")
    assert "no style guide" in text.lower() or "missing" in text.lower()


# --- Knowledge base --------------------------------------------------------

def test_kb_save_and_search(tmp_data_dir):
    server.kb_save_snippet(
        title="Pre-commit",
        content="pre-commit install",
        tags="git,hooks",
        project="acme",
        client="acme-corp",
    )
    results = server.kb_search_snippets("pre-commit")
    assert "Pre-commit" in results


def test_kb_search_no_results(tmp_data_dir):
    assert "no snippets" in server.kb_search_snippets("zzz-no-match-zzz").lower()


def test_kb_save_insight(tmp_data_dir):
    server.kb_save_insight(text="Always lint before commit.", source="pairing")
    insights = server.kb_list_insights()
    assert "Always lint before commit." in insights


def test_kb_snippets_resource_by_tag(tmp_data_dir):
    server.kb_save_snippet(title="Make deploy", content="make deploy-staging",
                           tags="deploy,make")
    text = server.kb_snippets_resource(tag="deploy")
    assert "Make deploy" in text


def test_kb_insights_resource(tmp_data_dir):
    server.kb_save_insight(text="cache invalidation is hard", source="blog")
    text = server.kb_insights_resource()
    assert "cache invalidation is hard" in text


# --- Runbook wiring --------------------------------------------------------

def test_runbook_add_and_list(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.runbook_add(project="acme", name="deploy-staging",
                      command="make deploy-staging",
                      description="Deploy to staging")
    text = server.runbook_list("acme")
    assert "deploy-staging" in text


def test_runbook_run_dry_run(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.runbook_add(project="acme", name="deploy-staging",
                      command="make deploy-staging")
    text = server.runbook_run(project="acme", name="deploy-staging", dry_run=True)
    assert "[DRY RUN]" in text


def test_runbook_run_executes(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.runbook_add(project="acme", name="echo-hello",
                      command="echo hello world")
    fake = type("R", (), {"returncode": 0, "stdout": "hello world\n", "stderr": ""})()
    with patch("devflow_mcp.runbook.subprocess.run", return_value=fake):
        text = server.runbook_run(project="acme", name="echo-hello", dry_run=False)
    assert "Exit code: 0" in text
    assert "hello world" in text


def test_runbook_status_resource(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.runbook_add(project="acme", name="echo-hello", command="echo hi")
    text = server.runbook_resource("acme")
    assert "echo-hello" in text
    assert "echo hi" in text


# --- Mixed integration: snippet scoped to project+client -------------------

def test_project_scoped_snippet_search(tmp_data_dir):
    server.client_add(name="acme-corp")
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.kb_save_snippet(title="Migrations", content="alembic upgrade head",
                           tags="db", project="acme", client="acme-corp")
    server.kb_save_snippet(title="Other", content="something unrelated",
                           tags="misc", project="other", client="other")
    text = server.kb_search_snippets("alembic")
    assert "Migrations" in text
    assert "Other" not in text
