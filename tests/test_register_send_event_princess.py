import asyncio

import bot_core


class FakeRole:
    def __init__(self, role_id: int):
        self.id = role_id


class FakeMember:
    def __init__(self, user_id: int, display_name: str):
        self.id = user_id
        self.display_name = display_name
        self.roles = []
        self.guild = None


def test_register_send_event_stores_princess_metadata_and_keeps_rank_logic_generic():
    sub = FakeMember(200, "Sub User")
    princess = FakeMember(100, "Princess One")

    # Keep rank tiers empty so rank sync path is simple and deterministic.
    result = asyncio.run(
        bot_core.register_send_event(
            sub,
            amount=40.0,
            source="manual",
            princess_member=princess,
        )
    )

    assert result["amount"] == 40.0
    assert result["source"] == "manual"

    data = bot_core.load_stats()
    stats = bot_core.get_user_stats_blob(data, sub.id)
    assert stats["total_sent"] == 40.0
    assert stats["send_count"] == 1

    event = stats["send_history"][0]
    assert event["amount"] == 40.0
    assert event["source"] == "manual"
    assert event["princess_user_id"] == 100
    assert event["princess_display_name"] == "Princess One"

    # Rank calculation still depends only on totals/averages, not princess metadata.
    bot_core.RANK_TIERS = [{"role_id": 555, "avg_weekly": 10.0}]
    assert bot_core.rank_for_stats(stats) == "555"


def test_normalize_user_stats_shape_backfills_princess_fields():
    stats = {
        "total_sent": 10.0,
        "send_count": 1,
        "last_send_date": "2026-03-18",
        "display_name": "Sub",
        "send_history": [
            {"date": "2026-03-18", "amount": 10.0, "source": "manual", "princess_user_id": "777"},
            {"date": "2026-03-18", "amount": 5.0, "source": "manual"},
        ],
    }

    normalized = bot_core.normalize_user_stats_shape(stats)
    first = normalized["send_history"][0]
    second = normalized["send_history"][1]

    assert first["princess_user_id"] == 777
    assert first["princess_display_name"] is None

    assert second["princess_user_id"] is None
    assert second["princess_display_name"] is None
