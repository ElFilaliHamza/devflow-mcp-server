import json

from devflow_mcp import paths
from devflow_mcp.config_store import load_config, save_config


def test_load_config_returns_defaults_when_missing(tmp_data_dir):
    config = load_config()
    assert config == {"projects": {}, "clients": {}, "current_project": None}
    assert not paths.CONFIG_PATH.exists()


def test_save_then_load_roundtrip(tmp_data_dir):
    original = {
        "projects": {"acme": {"name": "acme", "path": "/tmp/acme", "client": "acme-corp"}},
        "clients": {"acme-corp": {"name": "acme-corp", "website": "https://acme.test"}},
        "current_project": "acme",
    }
    save_config(original)
    assert paths.CONFIG_PATH.exists()

    on_disk = json.loads(paths.CONFIG_PATH.read_text())
    assert on_disk == original

    reloaded = load_config()
    assert reloaded == original


def test_save_config_creates_file_with_indent(tmp_data_dir):
    save_config({"projects": {}, "clients": {}, "current_project": None})
    text = paths.CONFIG_PATH.read_text()
    # Indented JSON for human readability.
    assert "\n  " in text
