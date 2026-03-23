from datetime import date

from bot_commands.progression_commands import _leaderboard_value_for_period


def test_leaderboard_total_sent_filters_by_princess_for_all_time():
    stats = {
        "send_history": [
            {"date": "2026-03-10", "amount": 10.0, "princess_user_id": 1},
            {"date": "2026-03-11", "amount": 20.0, "princess_user_id": 2},
            {"date": "2026-03-12", "amount": 30.0, "princess_user_id": 1},
        ],
        "total_sent": 60.0,
    }

    all_total = _leaderboard_value_for_period(
        stats,
        metric_key="total_sent",
        period_key="all",
        period_start=None,
        period_end=None,
        princess_user_id=None,
    )
    princess_1_total = _leaderboard_value_for_period(
        stats,
        metric_key="total_sent",
        period_key="all",
        period_start=None,
        period_end=None,
        princess_user_id=1,
    )
    princess_2_total = _leaderboard_value_for_period(
        stats,
        metric_key="total_sent",
        period_key="all",
        period_start=None,
        period_end=None,
        princess_user_id=2,
    )

    assert all_total == 60.0
    assert princess_1_total == 40.0
    assert princess_2_total == 20.0


def test_leaderboard_avg_weekly_filters_by_princess_in_date_window():
    stats = {
        "send_history": [
            {"date": "2026-03-01", "amount": 14.0, "princess_user_id": 7},
            {"date": "2026-03-02", "amount": 7.0, "princess_user_id": 8},
            {"date": "2026-03-07", "amount": 7.0, "princess_user_id": 7},
        ],
        "total_sent": 28.0,
    }

    # Week window: 7 days => effective_weeks = 1.0
    start = date.fromisoformat("2026-03-01")
    end = date.fromisoformat("2026-03-07")

    avg_all = _leaderboard_value_for_period(
        stats,
        metric_key="avg_weekly",
        period_key="week",
        period_start=start,
        period_end=end,
        princess_user_id=None,
    )
    avg_for_7 = _leaderboard_value_for_period(
        stats,
        metric_key="avg_weekly",
        period_key="week",
        period_start=start,
        period_end=end,
        princess_user_id=7,
    )

    assert avg_all == 28.0
    assert avg_for_7 == 21.0
