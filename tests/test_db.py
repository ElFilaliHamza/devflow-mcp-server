from devflow_mcp import paths
from devflow_mcp.db import fetch_all_insights, fetch_all_snippets, init_db


def test_init_db_creates_db_file(tmp_data_dir):
    assert not paths.DB_PATH.exists()
    init_db()
    assert paths.DB_PATH.exists()


def test_init_db_is_idempotent(tmp_data_dir):
    init_db()
    init_db()  # must not raise
    assert paths.DB_PATH.exists()


def test_snippet_and_insight_roundtrip(tmp_data_dir):
    init_db()
    from devflow_mcp.db import insert_insight, insert_snippet

    insert_snippet(
        title="Pre-commit hook",
        content="pre-commit install",
        tags="git,hooks",
        project="acme",
        client="acme-corp",
    )
    insert_snippet(
        title="Make targets",
        content="make deploy-staging",
        tags="deploy,make",
        project="acme",
        client="",
    )
    insert_insight(text="Always run lint before commit.", source="pairing with Alex")

    snippets = fetch_all_snippets()
    assert len(snippets) == 2
    titles = {s["title"] for s in snippets}
    assert titles == {"Pre-commit hook", "Make targets"}

    insights = fetch_all_insights()
    assert len(insights) == 1
    assert insights[0]["text"] == "Always run lint before commit."
    assert insights[0]["source"] == "pairing with Alex"
