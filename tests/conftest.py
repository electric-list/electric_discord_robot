from pathlib import Path

import pytest

import bot_core


@pytest.fixture(autouse=True)
def isolated_files(tmp_path, monkeypatch):
    """Redirect bot_core persistence files to a temporary test directory."""
    monkeypatch.setattr(bot_core, "stats_file", Path(tmp_path / "progression_data.json"))
    monkeypatch.setattr(bot_core, "bot_settings_file", Path(tmp_path / "bot_settings.json"))
    monkeypatch.setattr(bot_core, "rank_config_file", Path(tmp_path / "rank_config.json"))
    monkeypatch.setattr(bot_core, "pending_views_file", Path(tmp_path / "pending_views.json"))

    # Reset in-memory state so each test starts clean.
    monkeypatch.setattr(bot_core, "RANK_TIERS", [])
    monkeypatch.setattr(
        bot_core,
        "BOT_SETTINGS",
        {
            "rank_update_channel_id": None,
            "rank_update_channel_name": "JordanBot",
            "tributes_channel_id": None,
            "tributes_channel_name": "tributes",
            "princess_role_id": None,
            "admin_role_ids": [],
            "common_role_ids": [],
        },
    )

    yield
