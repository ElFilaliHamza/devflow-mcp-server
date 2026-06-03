import pytest

from devflow_mcp import server
from devflow_mcp.config_store import load_config
from devflow_mcp.paths import CONFIG_PATH


# --- Project tools ---------------------------------------------------------

def test_project_onboard_creates_project_and_scans(tmp_path, tmp_data_dir):
    # Create a fake project on disk.
    (tmp_path / "README.md").write_text("# Acme Web\n\nThe Acme marketing site.", encoding="utf-8")
    (tmp_path / ".env.example").write_text("API_KEY=\nDB_URL=\n", encoding="utf-8")

    result = server.project_onboard(
        name="acme",
        path=str(tmp_path),
        client="acme-corp",
        description="Marketing site",
        stack="nextjs",
    )
    assert "acme" in result
    assert "README" in result or "Readme" in result or "readme" in result.lower()

    cfg = load_config()
    assert "acme" in cfg["projects"]
    proj = cfg["projects"]["acme"]
    assert proj["client"] == "acme-corp"
    assert proj["stack"] == "nextjs"
    assert "Acme Web" in proj["readme_summary"]
    assert proj["env_template"] == "API_KEY=\nDB_URL=\n"


def test_project_list_returns_names(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    server.project_onboard(name="bravo", path="/tmp/bravo", client="bravo-llc")
    result = server.project_list()
    assert "acme" in result
    assert "bravo" in result


def test_project_set_current_persists_choice(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp")
    result = server.project_set_current("acme")
    assert "acme" in result
    assert load_config()["current_project"] == "acme"


def test_project_set_current_unknown_raises(tmp_data_dir):
    with pytest.raises(KeyError):
        server.project_set_current("ghost")


def test_current_project_resource(tmp_data_dir):
    server.project_onboard(name="acme", path="/tmp/acme", client="acme-corp",
                            description="the marketing site")
    server.project_set_current("acme")
    text = server.current_project_resource()
    assert "acme" in text
    assert "the marketing site" in text


# --- Project resource -------------------------------------------------------

def test_project_readme_resource(tmp_path, tmp_data_dir):
    (tmp_path / "README.md").write_text("# Title\nBody text.", encoding="utf-8")
    server.project_onboard(name="acme", path=str(tmp_path), client="acme-corp")
    assert "Title" in server.project_readme_resource("acme")
    assert "Body text." in server.project_readme_resource("acme")


def test_project_readme_resource_missing(tmp_data_dir):
    server.project_onboard(name="ghost", path="/nope", client="none")
    assert "not found" in server.project_readme_resource("ghost").lower()


# --- Client tools -----------------------------------------------------------

def test_client_add_and_list(tmp_data_dir):
    server.client_add(name="acme-corp", website="https://acme.test", notes="Net 30")
    server.client_add(name="bravo-llc", website="https://bravo.test", notes="")
    text = server.client_list()
    assert "acme-corp" in text
    assert "bravo-llc" in text
