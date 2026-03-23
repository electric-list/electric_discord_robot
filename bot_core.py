import io
import json
import math
import random
import random
from datetime import date, timedelta
from pathlib import Path

import discord
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import styles


pending_views_file = Path("pending_views.json")
stats_file = Path("progression_data.json")
rank_config_file = Path("rank_config.json")
bot_settings_file = Path("bot_settings.json")


default_rank_tiers: list[dict] = []

RANK_TIERS = list(default_rank_tiers)
BOT_SETTINGS = {
    "rank_update_channel_id": None,
    "rank_update_channel_name": "JordanBot",
    "tributes_channel_id": None,
    "tributes_channel_name": "tributes",
    "princess_role_id": None,
    "admin_role_ids": [],
    "common_role_ids": [],
}


def initialize_runtime_state():
    global RANK_TIERS
    global BOT_SETTINGS
    RANK_TIERS = load_rank_tiers()
    BOT_SETTINGS = load_bot_settings()


def get_rank_tiers() -> list[dict]:
    return list(RANK_TIERS)


def require_any_role(role_ids_or_getter):
    async def predicate(interaction: discord.Interaction) -> bool:
        role_ids = role_ids_or_getter() if callable(role_ids_or_getter) else role_ids_or_getter
        role_ids = [int(role_id) for role_id in role_ids]
        if isinstance(interaction.user, discord.Member):
            if not role_ids and interaction.user.guild_permissions.administrator:
                return True
            user_role_ids = {role.id for role in interaction.user.roles}
            if any(role_id in user_role_ids for role_id in role_ids):
                return True

        role_mentions = " ".join(f"<@&{role_id}>" for role_id in role_ids)
        if not role_mentions:
            role_mentions = "(none configured yet - administrator required)"
        raise app_commands.CheckFailure(
            f"You need one of these roles to use this command: {role_mentions}"
        )

    return app_commands.check(predicate)


async def send_interaction_error(interaction: discord.Interaction, message: str):
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def default_user_stats() -> dict:
    return {
        "total_sent": 0.0,
        "send_count": 0,
        "last_send_date": None,
        "display_name": None,
        "send_history": [],
    }

"""Sort rank tiers by avg_weekly ascending, returns list of (role_id, avg_weekly) maps"""
def normalize_rank_tiers(raw_tiers) -> list[dict]:
    if not isinstance(raw_tiers, list):
        return list(default_rank_tiers)

    normalized: list[dict] = []
    for tier in raw_tiers:
        if not isinstance(tier, dict):
            continue
        role_id = tier.get("role_id")
        avg_weekly = tier.get("avg_weekly")
        try:
            role_id_value = int(role_id)
            avg_value = float(avg_weekly)
        except (TypeError, ValueError):
            continue
        if avg_value < 0 or role_id_value <= 0:
            continue
        normalized.append({"role_id": role_id_value, "avg_weekly": round(avg_value, 2)})

    if not normalized:
        return list(default_rank_tiers)

    normalized.sort(key=lambda item: float(item["avg_weekly"]))
    return normalized


def load_rank_tiers() -> list[dict]:
    if not rank_config_file.exists():
        save_rank_tiers(list(default_rank_tiers))
        return list(default_rank_tiers)

    try:
        with rank_config_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = {"tiers": list(default_rank_tiers)}

    tiers = normalize_rank_tiers(data.get("tiers"))
    save_rank_tiers(tiers)
    return tiers


def save_rank_tiers(tiers: list[dict]):
    normalized = normalize_rank_tiers(tiers)
    with rank_config_file.open("w", encoding="utf-8") as f:
        json.dump({"tiers": normalized}, f, indent=2)


def upsert_rank_tier_by_id(role_id: int, avg_weekly: float):
    global RANK_TIERS
    updated = False
    new_tiers = []
    for tier in RANK_TIERS:
        if int(tier["role_id"]) == int(role_id):
            new_tiers.append({"role_id": int(role_id), "avg_weekly": round(float(avg_weekly), 2)})
            updated = True
        else:
            new_tiers.append({"role_id": int(tier["role_id"]), "avg_weekly": float(tier["avg_weekly"])})

    if not updated:
        new_tiers.append({"role_id": int(role_id), "avg_weekly": round(float(avg_weekly), 2)})

    RANK_TIERS = normalize_rank_tiers(new_tiers)
    save_rank_tiers(RANK_TIERS)


def remove_rank_tier_by_id(role_id: int) -> bool:
    global RANK_TIERS
    filtered = [tier for tier in RANK_TIERS if int(tier["role_id"]) != int(role_id)]
    if len(filtered) == len(RANK_TIERS) or not filtered:
        return False

    RANK_TIERS = normalize_rank_tiers(filtered)
    save_rank_tiers(RANK_TIERS)
    return True


def reset_rank_tiers_to_default():
    global RANK_TIERS
    RANK_TIERS = normalize_rank_tiers(list(default_rank_tiers))
    save_rank_tiers(RANK_TIERS)


def normalize_bot_settings(raw: dict | None) -> dict:
    settings = {
        "rank_update_channel_id": None,
        "rank_update_channel_name": "JordanBot",
        "tributes_channel_id": None,
        "tributes_channel_name": "tributes",
        "princess_role_id": None,
        "admin_role_ids": [],
        "common_role_ids": [],
    }
    if not isinstance(raw, dict):
        return settings

    channel_id = raw.get("rank_update_channel_id")
    channel_name = raw.get("rank_update_channel_name")
    tributes_channel_id = raw.get("tributes_channel_id")
    tributes_channel_name = raw.get("tributes_channel_name")
    princess_role_id = raw.get("princess_role_id")
    admin_role_ids = raw.get("admin_role_ids")
    common_role_ids = raw.get("common_role_ids")

    if isinstance(channel_id, int):
        settings["rank_update_channel_id"] = channel_id
    elif isinstance(channel_id, str) and channel_id.isdigit():
        settings["rank_update_channel_id"] = int(channel_id)

    if isinstance(channel_name, str) and channel_name.strip():
        settings["rank_update_channel_name"] = channel_name.strip()

    if isinstance(tributes_channel_id, int):
        settings["tributes_channel_id"] = tributes_channel_id
    elif isinstance(tributes_channel_id, str) and tributes_channel_id.isdigit():
        settings["tributes_channel_id"] = int(tributes_channel_id)

    if isinstance(tributes_channel_name, str) and tributes_channel_name.strip():
        settings["tributes_channel_name"] = tributes_channel_name.strip()

    if isinstance(princess_role_id, int):
        settings["princess_role_id"] = princess_role_id if princess_role_id > 0 else None
    elif isinstance(princess_role_id, str) and princess_role_id.isdigit():
        value = int(princess_role_id)
        settings["princess_role_id"] = value if value > 0 else None

    if isinstance(admin_role_ids, list):
        normalized_admin = []
        for role_id in admin_role_ids:
            try:
                value = int(role_id)
            except (TypeError, ValueError):
                continue
            if value > 0:
                normalized_admin.append(value)
        settings["admin_role_ids"] = sorted(set(normalized_admin))

    if isinstance(common_role_ids, list):
        normalized_common = []
        for role_id in common_role_ids:
            try:
                value = int(role_id)
            except (TypeError, ValueError):
                continue
            if value > 0:
                normalized_common.append(value)
        settings["common_role_ids"] = sorted(set(normalized_common))

    return settings


def get_access_role_ids(group: str) -> list[int]:
    if group == "admin":
        return list(BOT_SETTINGS.get("admin_role_ids", []))
    if group == "common":
        return list(BOT_SETTINGS.get("common_role_ids", []))
    return []


def add_access_role(group: str, role_id: int):
    settings = dict(BOT_SETTINGS)
    key = "admin_role_ids" if group == "admin" else "common_role_ids"
    role_ids = list(settings.get(key, []))
    if int(role_id) not in role_ids:
        role_ids.append(int(role_id))
    settings[key] = sorted(set(role_ids))
    save_bot_settings(settings)


def remove_access_role(group: str, role_id: int):
    settings = dict(BOT_SETTINGS)
    key = "admin_role_ids" if group == "admin" else "common_role_ids"
    role_ids = [rid for rid in settings.get(key, []) if int(rid) != int(role_id)]
    settings[key] = role_ids
    save_bot_settings(settings)


def clear_access_roles(group: str):
    settings = dict(BOT_SETTINGS)
    key = "admin_role_ids" if group == "admin" else "common_role_ids"
    settings[key] = []
    save_bot_settings(settings)


def load_bot_settings() -> dict:
    if not bot_settings_file.exists():
        save_bot_settings(BOT_SETTINGS)
        return normalize_bot_settings(BOT_SETTINGS)

    try:
        with bot_settings_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = None

    normalized = normalize_bot_settings(data)
    save_bot_settings(normalized)
    return normalized


def save_bot_settings(settings: dict):
    global BOT_SETTINGS
    normalized = normalize_bot_settings(settings)
    with bot_settings_file.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2)
    BOT_SETTINGS = normalized


def set_rank_update_channel(channel_id: int | None, fallback_name: str | None = None):
    settings = dict(BOT_SETTINGS)
    settings["rank_update_channel_id"] = channel_id
    if fallback_name and fallback_name.strip():
        settings["rank_update_channel_name"] = fallback_name.strip()
    save_bot_settings(settings)


def get_rank_update_channel_settings() -> dict:
    return dict(BOT_SETTINGS)


def set_tributes_channel(channel_id: int | None, fallback_name: str | None = None):
    settings = dict(BOT_SETTINGS)
    settings["tributes_channel_id"] = channel_id
    if fallback_name and fallback_name.strip():
        settings["tributes_channel_name"] = fallback_name.strip()
    save_bot_settings(settings)


def get_tributes_channel_settings() -> dict:
    return dict(BOT_SETTINGS)


def get_princess_role_id() -> int | None:
    value = BOT_SETTINGS.get("princess_role_id")
    return int(value) if isinstance(value, int) and value > 0 else None


def set_princess_role(role_id: int | None):
    settings = dict(BOT_SETTINGS)
    settings["princess_role_id"] = int(role_id) if role_id is not None else None
    save_bot_settings(settings)


def is_princess_member(member: discord.Member) -> bool:
    role_id = get_princess_role_id()
    if role_id is None:
        return False
    return has_any_role_id(member, [role_id])


def load_stats() -> dict:
    if not stats_file.exists():
        return {"users": {}}

    try:
        with stats_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "users" not in data or not isinstance(data["users"], dict):
            return {"users": {}}
        return data
    except (json.JSONDecodeError, OSError):
        return {"users": {}}


def save_stats(data: dict):
    with stats_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _recalculate_send_stats(stats: dict):
    history = stats.get("send_history", [])
    if not isinstance(history, list):
        history = []
        stats["send_history"] = history

    stats["total_sent"] = round(
        sum(float(event.get("amount", 0.0)) for event in history if isinstance(event, dict)),
        2,
    )
    stats["send_count"] = len(history)

    valid_dates = [
        str(event.get("date", ""))
        for event in history
        if isinstance(event, dict) and isinstance(event.get("date"), str)
    ]
    stats["last_send_date"] = max(valid_dates, default="")


def remove_send_event(
    user_id: int,
    event_index: int,
    expected_date: str | None = None,
    expected_amount: float | None = None,
) -> tuple[bool, dict | None, float | None]:
    """Remove a send by index after confirming its expected data. Returns success, updated stats, and removed amount."""
    data = load_stats()
    users = data.get("users", {})
    key = str(user_id)
    if key not in users:
        return False, None, None

    stats = normalize_user_stats_shape(users[key])
    history = stats.get("send_history", [])
    if not isinstance(history, list) or event_index < 0 or event_index >= len(history):
        return False, None, None

    target_event = history[event_index]
    if not isinstance(target_event, dict):
        return False, None, None
    if expected_date is not None and str(target_event.get("date", "")) != expected_date:
        return False, None, None
    if expected_amount is not None and round(float(target_event.get("amount", 0.0)), 2) != round(float(expected_amount), 2):
        return False, None, None

    removed_amount = round(float(target_event.get("amount", 0.0)), 2)
    history.pop(event_index)
    stats["send_history"] = history
    _recalculate_send_stats(stats)
    save_stats(data)
    return True, stats, removed_amount


def apply_negative_send_adjustment(user_id: int, amount_to_remove: float) -> tuple[float, float, dict | None]:
    """Consume recent sends from newest to oldest and return (removed_amount, remaining_amount, stats)."""
    data = load_stats()
    users = data.get("users", {})
    key = str(user_id)
    if key not in users:
        return 0.0, round(amount_to_remove, 2), None

    stats = normalize_user_stats_shape(users[key])
    history = stats.get("send_history", [])
    if not isinstance(history, list):
        return 0.0, round(amount_to_remove, 2), stats

    remaining = round(max(0.0, amount_to_remove), 2)
    index = len(history) - 1
    while index >= 0 and remaining > 0:
        event = history[index]
        if not isinstance(event, dict):
            index -= 1
            continue

        event_amount = round(float(event.get("amount", 0.0)), 2)
        if event_amount <= 0:
            index -= 1
            continue

        if event_amount <= remaining:
            remaining = round(remaining - event_amount, 2)
            history.pop(index)
        else:
            event["amount"] = round(event_amount - remaining, 2)
            remaining = 0.0
        index -= 1

    stats["send_history"] = history
    _recalculate_send_stats(stats)
    save_stats(data)
    removed_amount = round(amount_to_remove - remaining, 2)
    return removed_amount, round(remaining, 2), stats


def default_pending_views() -> dict:
    return {"game": {}, "sub_claim": {}, "request": {}}


def load_pending_views() -> dict:
    if not pending_views_file.exists():
        return default_pending_views()

    try:
        with pending_views_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default_pending_views()
        data.setdefault("game", {})
        data.setdefault("sub_claim", {})
        data.setdefault("request", {})
        if not isinstance(data["game"], dict) or not isinstance(data["sub_claim"], dict) or not isinstance(data["request"], dict):
            return default_pending_views()
        return data
    except (json.JSONDecodeError, OSError):
        return default_pending_views()


def save_pending_views(data: dict):
    with pending_views_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def add_pending_game_view(
    message_id: int,
    target_user_id: int,
    amount: float,
    source: str,
    princess_user_id: int | None = None,
    princess_display_name: str | None = None,
):
    data = load_pending_views()
    data["game"][str(message_id)] = {
        "target_user_id": int(target_user_id),
        "amount": float(amount),
        "source": source,
        "recorded": False,
        "princess_user_id": int(princess_user_id) if princess_user_id is not None else None,
        "princess_display_name": str(princess_display_name) if princess_display_name else None,
    }
    save_pending_views(data)


def update_pending_game_princess(
    message_id: int,
    princess_user_id: int | None,
    princess_display_name: str | None,
):
    data = load_pending_views()
    key = str(message_id)
    game = data.get("game", {})
    if key in game:
        game[key]["princess_user_id"] = int(princess_user_id) if princess_user_id is not None else None
        game[key]["princess_display_name"] = str(princess_display_name) if princess_display_name else None
        save_pending_views(data)


def set_pending_game_recorded(message_id: int, recorded: bool):
    data = load_pending_views()
    key = str(message_id)
    game = data.get("game", {})
    if key in game:
        game[key]["recorded"] = bool(recorded)
        save_pending_views(data)


def add_pending_sub_claim_view(
    message_id: int,
    requester_id: int,
    amount: float,
    note: str | None,
    platform: str,
    reimbursement_item: str | None = None,
    request_message_id: int | None = None,
    delete_request_on_approve: bool = False,
    princess_user_id: int | None = None,
    princess_display_name: str | None = None,
):
    data = load_pending_views()
    data["sub_claim"][str(message_id)] = {
        "requester_id": int(requester_id),
        "amount": float(amount),
        "note": note,
        "platform": str(platform),
        "reimbursement_item": reimbursement_item,
        "request_message_id": int(request_message_id) if request_message_id else None,
        "delete_request_on_approve": bool(delete_request_on_approve),
        "princess_user_id": int(princess_user_id) if princess_user_id is not None else None,
        "princess_display_name": str(princess_display_name) if princess_display_name else None,
    }
    save_pending_views(data)


def add_pending_request_view(
    message_id: int,
    requester_mention: str,
    requested_amount: float,
    target_text: str,
    request_note: str | None,
    reimbursement_item: str | None,
    target_user_id: int | None,
    princess_user_id: int | None,
    princess_display_name: str | None,
):
    data = load_pending_views()
    data["request"][str(message_id)] = {
        "requester_mention": str(requester_mention),
        "requested_amount": float(requested_amount),
        "target_text": str(target_text),
        "request_note": request_note,
        "reimbursement_item": reimbursement_item,
        "target_user_id": int(target_user_id) if target_user_id is not None else None,
        "princess_user_id": int(princess_user_id) if princess_user_id is not None else None,
        "princess_display_name": str(princess_display_name) if princess_display_name else None,
    }
    save_pending_views(data)


def remove_pending_view(message_id: int, view_type: str):
    data = load_pending_views()
    key = str(message_id)
    bucket = data.get(view_type, {})
    if key in bucket:
        del bucket[key]
        save_pending_views(data)


def normalize_user_stats_shape(stats: dict) -> dict:
    defaults = default_user_stats()
    for key, value in defaults.items():
        if key not in stats:
            stats[key] = value

    if not isinstance(stats.get("send_history"), list):
        stats["send_history"] = []

    for event in stats["send_history"]:
        if not isinstance(event, dict):
            continue
        princess_user_id = event.get("princess_user_id")
        if isinstance(princess_user_id, str) and princess_user_id.isdigit():
            event["princess_user_id"] = int(princess_user_id)
        elif not isinstance(princess_user_id, int):
            event["princess_user_id"] = None

        princess_display_name = event.get("princess_display_name")
        if princess_display_name is None:
            event["princess_display_name"] = None
        elif not isinstance(princess_display_name, str):
            event["princess_display_name"] = str(princess_display_name)

    return stats


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def avg_weekly_from_events(events: list[dict]) -> float:
    if not events:
        return 0.0

    dated_events: list[tuple[date, dict]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_date_raw = event.get("date")
        if not isinstance(event_date_raw, str):
            continue
        try:
            event_date = date.fromisoformat(event_date_raw)
        except ValueError:
            continue
        dated_events.append((event_date, event))

    if not dated_events:
        return 0.0

    first_day = min(event_day for event_day, _event in dated_events)
    first_week_start = week_start(first_day)
    elapsed_weeks = ((date.today() - first_week_start).days // 7) + 1
    elapsed_weeks = max(1, elapsed_weeks)
    total_amount = sum(float(event.get("amount", 0.0)) for _d, event in dated_events)
    return round(total_amount / elapsed_weeks, 2)


def iter_events_for_period(stats: dict, period_key: str):
    history = stats.get("send_history", [])
    if not isinstance(history, list):
        return

    if period_key == "all":
        for event in history:
            if isinstance(event, dict):
                yield event
        return

    today = date.today()
    if period_key == "week":
        start_date = today - timedelta(days=today.weekday())
    elif period_key == "month":
        start_date = today.replace(day=1)
    else:
        start_date = date.min

    for event in history:
        if not isinstance(event, dict):
            continue
        event_date_raw = event.get("date")
        if not isinstance(event_date_raw, str):
            continue
        try:
            event_date = date.fromisoformat(event_date_raw)
        except ValueError:
            continue
        if event_date >= start_date:
            yield event


def avg_weekly_for_stats(stats: dict, period_key: str = "all") -> float:
    all_events = list(iter_events_for_period(stats, period_key))
    average = avg_weekly_from_events(all_events)
    if average > 0:
        return average

    if period_key == "all":
        return round(float(stats.get("total_sent", 0.0)), 2)
    return 0.0


def leaderboard_metric_value(stats: dict, metric_key: str, period_key: str):
    if period_key == "all":
        if metric_key == "avg_weekly":
            return avg_weekly_for_stats(stats, "all")
        return float(stats.get("total_sent", 0.0))

    events = list(iter_events_for_period(stats, period_key))
    if metric_key == "avg_weekly":
        return avg_weekly_for_stats(stats, period_key)
    return round(sum(float(event.get("amount", 0.0)) for event in events), 2)


def rank_for_stats(stats: dict) -> str:
    tiers = get_rank_tiers()
    if not tiers:
        return ""

    eligible_rank_id: int | None = None
    avg_weekly = avg_weekly_for_stats(stats, "all")

    for tier in tiers:
        if avg_weekly >= float(tier["avg_weekly"]):
            eligible_rank_id = int(tier["role_id"])
    return str(eligible_rank_id) if eligible_rank_id is not None else ""


def get_member_rank_role_ids(member: discord.Member) -> list[int]:
    managed_rank_ids = {int(tier["role_id"]) for tier in get_rank_tiers()}
    return [role.id for role in member.roles if role.id in managed_rank_ids]


def resolve_rank_update_channel(guild: discord.Guild) -> discord.abc.Messageable | None:
    channel_id = BOT_SETTINGS.get("rank_update_channel_id")
    if isinstance(channel_id, int):
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel

    fallback_name = str(BOT_SETTINGS.get("rank_update_channel_name", "JordanBot"))
    for channel in guild.text_channels:
        if channel.name.lower() == fallback_name.lower():
            return channel
    return None


def resolve_tributes_channel(guild: discord.Guild) -> discord.abc.Messageable | None:
    channel_id = BOT_SETTINGS.get("tributes_channel_id")
    if isinstance(channel_id, int):
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel

    fallback_name = str(BOT_SETTINGS.get("tributes_channel_name", "tributes"))
    for channel in guild.text_channels:
        if channel.name.lower() == fallback_name.lower():
            return channel
    return None


async def post_tributes_message(guild: discord.Guild | None, message: str):
    if guild is None:
        return

    channel = resolve_tributes_channel(guild)
    if channel is None:
        return

    await channel.send(message)


async def announce_rank_change(
    member: discord.Member,
    old_rank_id: int | None,
    new_rank_id: int,
    amount: float,
    source: str,
    avg_weekly: float,
):
    if member.guild is None:
        return

    # Determine if this is a promotion or demotion by comparing tier order.
    tiers = get_rank_tiers()
    tier_order = {int(t["role_id"]): i for i, t in enumerate(tiers)}
    old_order = tier_order.get(old_rank_id, -1) if old_rank_id else -1
    new_order = tier_order.get(new_rank_id, -1)
    is_promotion = new_order > old_order

    # Only post for rank-ups (promotions).
    if not is_promotion:
        return

    channel = resolve_rank_update_channel(member.guild)
    if channel is None:
        return

    kit = styles.get()
    message = random.choice(kit.rank_up_messages).format(mention=member.mention)

    old_display = f"<@&{old_rank_id}>" if old_rank_id else "Unranked"
    new_display = f"<@&{new_rank_id}>"
    tier_change = kit.rank_up_tier_change.format(old=old_display, new=new_display)
    await channel.send(f"{message}\n{tier_change}")


async def sync_rank_role(member: discord.Member, stats: dict) -> tuple[str, list[str], bool]:
    if member.guild is None:
        return rank_for_stats(stats), [], False

    target_rank = rank_for_stats(stats)
    managed_role_ids = {int(tier["role_id"]) for tier in get_rank_tiers()}
    managed_roles = [role for role in member.guild.roles if role.id in managed_role_ids]

    if not target_rank:
        removed_role_names: list[str] = []
        for role in managed_roles:
            if role in member.roles:
                await member.remove_roles(role, reason="Progression rank update")
                removed_role_names.append(role.name)
        return "", removed_role_names, bool(removed_role_names)

    target_role_id = int(target_rank)

    target_role = member.guild.get_role(target_role_id)
    if target_role is None:
        return target_rank, [], False

    removed_role_names: list[str] = []
    had_target_role = target_role in member.roles
    for role in managed_roles:
        if role.id != target_role_id and role in member.roles:
            await member.remove_roles(role, reason="Progression rank update")
            removed_role_names.append(role.name)

    if target_role not in member.roles:
        await member.add_roles(target_role, reason="Progression rank update")

    changed = bool(removed_role_names) or not had_target_role
    return target_rank, removed_role_names, changed


async def register_send_event(
    member: discord.Member,
    amount: float,
    source: str,
    princess_member: discord.Member | None = None,
) -> dict:
    data = load_stats()
    stats = get_user_stats_blob(data, member.id)

    today_iso = date.today().isoformat()
    stats["display_name"] = member.display_name

    removed_amount = 0.0
    remaining_adjustment = 0.0
    if amount >= 0:
        stats["last_send_date"] = today_iso
        stats["total_sent"] = round(float(stats.get("total_sent", 0.0)) + amount, 2)
        stats["send_count"] = int(stats.get("send_count", 0)) + 1

        send_history = stats.setdefault("send_history", [])
        send_history.append(
            {
                "date": today_iso,
                "amount": float(amount),
                "display_name": member.display_name,
                "source": source,
                "princess_user_id": princess_member.id if princess_member is not None else None,
                "princess_display_name": princess_member.display_name if princess_member is not None else None,
            }
        )
        if len(send_history) > 10000:
            stats["send_history"] = send_history[-10000:]

        save_stats(data)
    else:
        removed_amount, remaining_adjustment, updated_stats = apply_negative_send_adjustment(member.id, abs(amount))
        if updated_stats is not None:
            stats = updated_stats
        stats["display_name"] = member.display_name
        data = load_stats()
        saved_stats = get_user_stats_blob(data, member.id)
        saved_stats.update(stats)
        save_stats(data)

    previous_rank_ids = get_member_rank_role_ids(member)
    previous_rank_id = previous_rank_ids[0] if previous_rank_ids else None

    # Calculate target rank independently so announcement fires even if Discord role API fails.
    target_rank = rank_for_stats(stats)
    target_rank_id = int(target_rank) if target_rank else 0
    rank_changed = target_rank_id > 0 and previous_rank_id != target_rank_id

    removed_ranks: list[str] = []
    role_sync_failed = False
    try:
        _, removed_ranks, _ = await sync_rank_role(member, stats)
    except (discord.Forbidden, discord.HTTPException):
        role_sync_failed = True

    avg_weekly = avg_weekly_for_stats(stats, "all")
    if rank_changed:
        try:
            await announce_rank_change(member, previous_rank_id, target_rank_id, amount, source, avg_weekly)
        except Exception:
            pass

    return {
        "source": source,
        "amount": amount,
        "stats": stats,
        "role_sync_failed": role_sync_failed,
        "removed_amount": removed_amount,
        "remaining_adjustment": remaining_adjustment,
        "rank": f"<@&{target_rank_id}>" if target_rank_id > 0 else "Unranked",
        "removed_ranks": removed_ranks,
        "rank_changed": rank_changed,
    }


def get_user_stats_blob(data: dict, user_id: int) -> dict:
    users = data.setdefault("users", {})
    key = str(user_id)
    if key not in users or not isinstance(users[key], dict):
        users[key] = default_user_stats()
    return normalize_user_stats_shape(users[key])


def has_named_role(member: discord.Member, role_name: str) -> bool:
    raise NotImplementedError("Use has_any_role_id")


def has_any_role_id(member: discord.Member, role_ids: list[int]) -> bool:
    member_role_ids = {role.id for role in member.roles}
    return any(int(role_id) in member_role_ids for role_id in role_ids)


def format_record_result(member: discord.Member, amount: float, source: str, result: dict) -> str:
    kit = styles.get()
    source_suffix = "" if source.strip().lower() == "manual" else f" via {source}"
    if amount >= 0:
        lines = [
            kit.tpl_tribute_positive.format(mention=member.mention, amount=amount, source_suffix=source_suffix),
        ]
    else:
        removed_amount = float(result.get("removed_amount", 0.0))
        remaining_adjustment = float(result.get("remaining_adjustment", 0.0))
        lines = [
            kit.tpl_tribute_negative.format(
                mention=member.mention,
                adj_amount=abs(amount),
                source_suffix=source_suffix,
                removed_amount=removed_amount,
            ),
        ]
        if remaining_adjustment > 0:
            lines.append(kit.tpl_tribute_negative_remainder.format(remaining=remaining_adjustment))
        lines.append(kit.tpl_tribute_negative_rank.format(rank=result["rank"]))
    if result.get("role_sync_failed"):
        lines.append(kit.tpl_tribute_role_warning)
    return "\n".join(lines)


class RecordSendFromGameView(discord.ui.View):
    def __init__(
        self,
        target_user_id: int,
        amount: float,
        source: str,
        recorded: bool = False,
        princess_user_id: int | None = None,
        princess_display_name: str | None = None,
    ):
        super().__init__(timeout=None)
        self.target_user_id = target_user_id
        self.amount = amount
        self.source = source
        self.recorded = recorded
        self.princess_user_id = princess_user_id
        self.princess_display_name = princess_display_name
        kit = styles.get()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "game_record_send":
                    child.label = kit.btn_record_send
                elif child.custom_id == "game_delete_message":
                    child.label = kit.btn_delete_message
        if self.recorded:
            self.disable_record_button()

    def disable_record_button(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button) and child.custom_id == "game_record_send":
                child.disabled = True

    @discord.ui.button(label="Record Send", style=discord.ButtonStyle.success, custom_id="game_record_send")
    async def record_send_button(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member) or not has_any_role_id(interaction.user, get_access_role_ids("admin")):
            await interaction.response.send_message(
                "Only members with an admin access role can use this button.",
                ephemeral=True,
            )
            return

        if self.recorded:
            await interaction.response.send_message(
                "This send was already recorded.", ephemeral=True
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Guild not available.", ephemeral=True)
            return

        member = guild.get_member(self.target_user_id)
        if member is None:
            try:
                member = await guild.fetch_member(self.target_user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await interaction.response.send_message(
                    "Could not find the target member in this server.", ephemeral=True
                )
                return

        princess_member = None
        if self.princess_user_id is not None:
            princess_member = guild.get_member(self.princess_user_id)
            if princess_member is None:
                try:
                    princess_member = await guild.fetch_member(self.princess_user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    princess_member = None

        if princess_member is None and isinstance(interaction.user, discord.Member):
            princess_member = interaction.user

        result = await register_send_event(member, self.amount, self.source, princess_member=princess_member)
        self.recorded = True
        self.disable_record_button()

        if interaction.message is not None:
            set_pending_game_recorded(interaction.message.id, True)
            update_pending_game_princess(
                interaction.message.id,
                princess_member.id if princess_member is not None else None,
                princess_member.display_name if princess_member is not None else self.princess_display_name,
            )
            await interaction.message.edit(view=self)

        base_message = format_record_result(member, self.amount, self.source, result)
        kit = styles.get()
        source_key = self.source.strip().lower()
        if source_key == "dice":
            tributes_message = f"{base_message}{kit.tpl_game_source_dice}"
        elif source_key == "wheelspin":
            tributes_message = f"{base_message}{kit.tpl_game_source_wheelspin}"
        else:
            tributes_message = base_message

        tributes_channel = resolve_tributes_channel(guild)
        current_channel_id = getattr(interaction.channel, "id", None)
        if tributes_channel is not None and tributes_channel.id == current_channel_id:
            await interaction.channel.send(tributes_message)
            await interaction.response.defer()
            return

        await post_tributes_message(guild, tributes_message)
        await interaction.response.send_message(base_message, ephemeral=True)

    @discord.ui.button(label="Delete Message", style=discord.ButtonStyle.danger, custom_id="game_delete_message")
    async def delete_message_button(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member) or not has_any_role_id(interaction.user, get_access_role_ids("admin")):
            await interaction.response.send_message(
                "Only members with an admin access role can delete this message.",
                ephemeral=True,
            )
            return

        if interaction.message is None:
            await interaction.response.send_message("Message not found.", ephemeral=True)
            return

        remove_pending_view(interaction.message.id, "game")
        await interaction.message.delete()


class SendProofModal(discord.ui.Modal):
    def __init__(self, request_view: "RequestView", original_interaction: discord.Interaction):
        kit = styles.get()
        super().__init__(title=kit.modal_send_proof_title)
        self.request_view = request_view
        self.original_interaction = original_interaction
        self.amount_input = discord.ui.TextInput(
            label=kit.modal_amount_label,
            placeholder=kit.modal_amount_placeholder,
            required=True,
        )
        self.proof_input = discord.ui.TextInput(
            label=kit.modal_note_label,
            placeholder=kit.modal_note_placeholder,
            required=False,
        )
        self.platform_input = discord.ui.TextInput(
            label=kit.modal_platform_label,
            placeholder=kit.modal_platform_placeholder,
            required=True,
        )
        self.add_item(self.amount_input)
        self.add_item(self.platform_input)
        self.add_item(self.proof_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amount = float(self.amount_input.value)
        except ValueError:
            await interaction.response.send_message(
                "Invalid amount. Please enter a valid number.",
                ephemeral=True,
            )
            return

        if amount <= 0:
            await interaction.response.send_message(
                "Amount must be greater than 0.",
                ephemeral=True,
            )
            return

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Could not resolve member.",
                ephemeral=True,
            )
            return

        proof = self.proof_input.value.strip() if self.proof_input.value else None
        platform = self.platform_input.value.strip()
        if not platform:
            await interaction.response.send_message(
                "Platform is required.",
                ephemeral=True,
            )
            return
        
        # Build the claim message with request context
        if self.request_view.reimbursement_item:
            request_context = (
                f" in response to {self.request_view.requester_mention}'s reimbursement request"
                f" for {self.request_view.reimbursement_item} ({self.request_view.requested_amount:.2f})"
            )
        else:
            request_context = f" in response to {self.request_view.requester_mention}'s request of {self.request_view.requested_amount:.2f}"

        if self.request_view.request_note:
            request_context += f"\nRequest note: {self.request_view.request_note}"

        proof_text = f"\nNote: {proof}" if proof else ""

        # Create the sub-claim view
        view = SubSendClaimView(
            interaction.user.id,
            amount,
            proof,
            platform,
            self.request_view.reimbursement_item,
            self.original_interaction.message.id if self.original_interaction.message is not None else None,
            self.request_view.target_user_id is not None,
            self.request_view.princess_user_id,
            self.request_view.princess_display_name,
        )
        if self.request_view.reimbursement_item:
            message_text = styles.get().tpl_claim_reimburse.format(
                mention=interaction.user.mention,
                amount=amount,
                platform=platform,
                item=self.request_view.reimbursement_item,
                request_context=request_context,
                proof_text=proof_text,
            )
        else:
            message_text = styles.get().tpl_claim_sent.format(
                mention=interaction.user.mention,
                amount=amount,
                platform=platform,
                request_context=request_context,
                proof_text=proof_text,
            )
        
        # Send to the same channel, replying to the original request if possible
        channel = interaction.channel
        try:
            if self.original_interaction.message is not None:
                sent_message = await channel.send(
                    message_text,
                    view=view,
                    reference=self.original_interaction.message,
                )
            else:
                sent_message = await channel.send(
                    message_text,
                    view=view,
                )
        except discord.HTTPException:
            sent_message = await channel.send(
                message_text,
                view=view,
            )
        
        add_pending_sub_claim_view(
            sent_message.id,
            interaction.user.id,
            amount,
            proof,
            platform,
            self.request_view.reimbursement_item,
            self.original_interaction.message.id if self.original_interaction.message is not None else None,
            self.request_view.target_user_id is not None,
            self.request_view.princess_user_id,
            self.request_view.princess_display_name,
        )

        await interaction.response.defer()


class RequestView(discord.ui.View):
    def __init__(
        self,
        requester_mention: str,
        requested_amount: float,
        target_text: str,
        request_note: str | None,
        reimbursement_item: str | None = None,
        target_user_id: int | None = None,
        princess_user_id: int | None = None,
        princess_display_name: str | None = None,
    ):
        super().__init__(timeout=None)
        self.requester_mention = requester_mention
        self.requested_amount = requested_amount
        self.target_text = target_text
        self.request_note = request_note
        self.reimbursement_item = reimbursement_item
        self.target_user_id = target_user_id
        self.princess_user_id = princess_user_id
        self.princess_display_name = princess_display_name
        kit = styles.get()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "request_i_sent":
                    child.label = kit.btn_i_sent
                elif child.custom_id == "request_delete":
                    child.label = kit.btn_delete_request

    @discord.ui.button(label="I Sent", style=discord.ButtonStyle.primary, custom_id="request_i_sent")
    async def i_sent_button(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Could not resolve member.",
                ephemeral=True,
            )
            return

        if not has_any_role_id(interaction.user, get_access_role_ids("common")):
            await interaction.response.send_message(
                "Only members with the common access role can respond to requests.",
                ephemeral=True,
            )
            return

        if self.target_user_id is not None and interaction.user.id != self.target_user_id:
            await interaction.response.send_message(
                "Only the targeted user can respond to this request.",
                ephemeral=True,
            )
            return

        modal = SendProofModal(self, interaction)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="request_delete")
    async def delete_button(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member) or not has_any_role_id(interaction.user, get_access_role_ids("admin")):
            await interaction.response.send_message(
                "Only members with an admin access role can delete this request.",
                ephemeral=True,
            )
            return

        if interaction.message is None:
            await interaction.response.send_message("Message not found.", ephemeral=True)
            return

        remove_pending_view(interaction.message.id, "request")
        await interaction.message.delete()
        await interaction.response.defer()


class SubSendClaimView(discord.ui.View):
    def __init__(
        self,
        requester_id: int,
        amount: float,
        note: str | None,
        platform: str,
        reimbursement_item: str | None = None,
        request_message_id: int | None = None,
        delete_request_on_approve: bool = False,
        princess_user_id: int | None = None,
        princess_display_name: str | None = None,
    ):
        super().__init__(timeout=None)
        self.requester_id = requester_id
        self.amount = amount
        self.note = note
        self.platform = platform
        self.reimbursement_item = reimbursement_item
        self.request_message_id = request_message_id
        self.delete_request_on_approve = delete_request_on_approve
        self.princess_user_id = princess_user_id
        self.princess_display_name = princess_display_name
        self.done = False
        kit = styles.get()
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "sub_claim_approve":
                    child.label = kit.btn_approve_claim
                elif child.custom_id == "sub_claim_delete":
                    child.label = kit.btn_delete_claim

    def disable_all_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    @discord.ui.button(label="Approve and Record", style=discord.ButtonStyle.success, custom_id="sub_claim_approve")
    async def approve_button(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member) or not has_any_role_id(interaction.user, get_access_role_ids("admin")):
            await interaction.response.send_message(
                "Only members with an admin access role can approve this request.",
                ephemeral=True,
            )
            return

        if self.done:
            await interaction.response.send_message(
                "This request was already processed.", ephemeral=True
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Guild not available.", ephemeral=True)
            return

        requester = guild.get_member(self.requester_id)
        if requester is None:
            try:
                requester = await guild.fetch_member(self.requester_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                await interaction.response.send_message(
                    "Could not find the requesting member in this server.",
                    ephemeral=True,
                )
                return

        princess_member = None
        if self.princess_user_id is not None:
            princess_member = guild.get_member(self.princess_user_id)
            if princess_member is None:
                try:
                    princess_member = await guild.fetch_member(self.princess_user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    princess_member = None

        if princess_member is None and isinstance(interaction.user, discord.Member):
            princess_member = interaction.user

        result = await register_send_event(
            requester,
            self.amount,
            self.platform,
            princess_member=princess_member,
        )
        self.done = True
        self.disable_all_buttons()

        # Post to tributes using reimbursement text when applicable.
        kit = styles.get()
        if self.reimbursement_item:
            base_message = kit.tpl_approval_reimburse.format(
                mention=requester.mention,
                amount=self.amount,
                platform=self.platform,
                item=self.reimbursement_item,
            )
        else:
            base_message = format_record_result(requester, self.amount, self.platform, result)
        tributes_msg = f"{base_message}{kit.tpl_approved_by.format(approver=interaction.user.mention)}"
        await post_tributes_message(interaction.guild, tributes_msg)
        
        if interaction.message is not None:
            # Delete the sub-claim message
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                pass
            remove_pending_view(interaction.message.id, "sub_claim")

        if self.delete_request_on_approve and self.request_message_id and interaction.channel is not None:
            try:
                request_message = await interaction.channel.fetch_message(self.request_message_id)
                await request_message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException, AttributeError):
                pass

        # Only send ephemeral confirmation if we are not already in the tributes channel.
        tributes_channel = resolve_tributes_channel(interaction.guild) if interaction.guild else None
        current_channel_id = getattr(interaction.channel, "id", None)
        if tributes_channel is None or tributes_channel.id != current_channel_id:
            await interaction.response.send_message(base_message, ephemeral=True)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Delete Request", style=discord.ButtonStyle.danger, custom_id="sub_claim_delete")
    async def delete_button(
        self, interaction: discord.Interaction, _button: discord.ui.Button
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Could not resolve member.", ephemeral=True)
            return

        is_admin = has_any_role_id(interaction.user, get_access_role_ids("admin"))
        is_requester = interaction.user.id == self.requester_id

        if not is_admin and not is_requester:
            await interaction.response.send_message(
                "Only the sub who submitted this request or an admin can delete it.",
                ephemeral=True,
            )
            return

        if interaction.message is None:
            await interaction.response.send_message("Message not found.", ephemeral=True)
            return

        remove_pending_view(interaction.message.id, "sub_claim")
        await interaction.message.delete()
        await interaction.response.defer()


def restore_persistent_views(client: discord.Client):
    pending = load_pending_views()

    for message_id_str, payload in pending.get("game", {}).items():
        try:
            message_id = int(message_id_str)
            target_user_id = int(payload["target_user_id"])
            amount = float(payload["amount"])
            source = str(payload["source"])
            recorded = bool(payload.get("recorded", False))
            princess_user_id = payload.get("princess_user_id")
            if princess_user_id is not None:
                princess_user_id = int(princess_user_id)
            princess_display_name = payload.get("princess_display_name")
            if princess_display_name is not None:
                princess_display_name = str(princess_display_name)
        except (KeyError, ValueError, TypeError):
            continue

        view = RecordSendFromGameView(
            target_user_id,
            amount,
            source,
            recorded=recorded,
            princess_user_id=princess_user_id,
            princess_display_name=princess_display_name,
        )
        client.add_view(view, message_id=message_id)

    for message_id_str, payload in pending.get("sub_claim", {}).items():
        try:
            message_id = int(message_id_str)
            requester_id = int(payload["requester_id"])
            amount = float(payload["amount"])
            note = payload.get("note")
            if note is not None:
                note = str(note)
            platform = payload.get("platform")
            if not isinstance(platform, str) or not platform.strip():
                platform = "sub-claim"
            reimbursement_item = payload.get("reimbursement_item")
            if reimbursement_item is not None:
                reimbursement_item = str(reimbursement_item)
            request_message_id = payload.get("request_message_id")
            if request_message_id is not None:
                request_message_id = int(request_message_id)
            delete_request_on_approve = bool(payload.get("delete_request_on_approve", False))
            princess_user_id = payload.get("princess_user_id")
            if princess_user_id is not None:
                princess_user_id = int(princess_user_id)
            princess_display_name = payload.get("princess_display_name")
            if princess_display_name is not None:
                princess_display_name = str(princess_display_name)
        except (KeyError, ValueError, TypeError):
            continue

        view = SubSendClaimView(
            requester_id,
            amount,
            note,
            platform,
            reimbursement_item,
            request_message_id,
            delete_request_on_approve,
            princess_user_id,
            princess_display_name,
        )
        client.add_view(view, message_id=message_id)

    for message_id_str, payload in pending.get("request", {}).items():
        try:
            message_id = int(message_id_str)
            requester_mention = str(payload["requester_mention"])
            requested_amount = float(payload["requested_amount"])
            target_text = str(payload.get("target_text", ""))
            request_note = payload.get("request_note")
            if request_note is not None:
                request_note = str(request_note)
            reimbursement_item = payload.get("reimbursement_item")
            if reimbursement_item is not None:
                reimbursement_item = str(reimbursement_item)
            target_user_id = payload.get("target_user_id")
            if target_user_id is not None:
                target_user_id = int(target_user_id)
            princess_user_id = payload.get("princess_user_id")
            if princess_user_id is not None:
                princess_user_id = int(princess_user_id)
            princess_display_name = payload.get("princess_display_name")
            if princess_display_name is not None:
                princess_display_name = str(princess_display_name)
        except (KeyError, ValueError, TypeError):
            continue

        view = RequestView(
            requester_mention,
            requested_amount,
            target_text,
            request_note,
            reimbursement_item,
            target_user_id,
            princess_user_id,
            princess_display_name,
        )
        client.add_view(view, message_id=message_id)


def _draw_centered_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, fill: tuple[int, int, int]):
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw.text((xy[0] - width // 2, xy[1] - height // 2), text, fill=fill, font=font)


def build_wheelspin_gif(min_value: int, max_value: int, result: int, spinner_name: str) -> io.BytesIO:
    width, height = 560, 560
    center = (width // 2, height // 2)
    outer_radius = 220
    inner_radius = 70
    pointer_y = center[1] - outer_radius - 18
    total_numbers = max_value - min_value + 1

    sample_count = min(total_numbers, 10)
    if sample_count <= 1:
        numbers = [result]
    elif sample_count == total_numbers:
        numbers = list(range(min_value, max_value + 1))
    else:
        max_offset = total_numbers - 1
        numbers = [
            min_value + int((i * max_offset) / (sample_count - 1))
            for i in range(sample_count)
        ]

    nearest_idx = min(range(len(numbers)), key=lambda i: abs(numbers[i] - result))
    numbers[nearest_idx] = result
    numbers = sorted(numbers)

    palette = [
        (239, 83, 80),
        (255, 167, 38),
        (102, 187, 106),
        (66, 165, 245),
        (171, 71, 188),
        (255, 238, 88),
    ]

    base_font = ImageFont.load_default()
    frames: list[Image.Image] = []
    frame_count = 38
    start_offset = random.uniform(0.0, 360.0)
    target_index = numbers.index(result)
    degrees_per_slot = 360.0 / len(numbers)
    # Align the center of the result slice with the top pointer (270 degrees).
    target_mid_angle = 270.0
    target_offset = (
        target_mid_angle - (target_index + 0.5) * degrees_per_slot
    ) % 360.0
    total_rotation = (target_offset - start_offset) % 360.0 + 1080.0

    for frame in range(frame_count):
        t = frame / (frame_count - 1)
        eased = 1 - (1 - t) ** 3
        offset = (start_offset + total_rotation * eased) % 360.0

        img = Image.new("RGB", (width, height), (24, 26, 31))
        draw = ImageDraw.Draw(img)

        draw.ellipse(
            (
                center[0] - outer_radius - 6,
                center[1] - outer_radius - 6,
                center[0] + outer_radius + 6,
                center[1] + outer_radius + 6,
            ),
            fill=(48, 52, 63),
        )

        for i, number in enumerate(numbers):
            start = offset + i * degrees_per_slot
            end = start + degrees_per_slot
            color = palette[i % len(palette)]
            draw.pieslice(
                (
                    center[0] - outer_radius,
                    center[1] - outer_radius,
                    center[0] + outer_radius,
                    center[1] + outer_radius,
                ),
                start=start,
                end=end,
                fill=color,
                outline=(22, 22, 24),
                width=2,
            )

            angle_mid = math.radians((start + end) / 2)
            label_r = (outer_radius + inner_radius) // 2
            lx = int(center[0] + math.cos(angle_mid) * label_r)
            ly = int(center[1] + math.sin(angle_mid) * label_r)
            _draw_centered_text(draw, (lx, ly), str(number), base_font, (15, 15, 15))

        draw.ellipse(
            (
                center[0] - inner_radius,
                center[1] - inner_radius,
                center[0] + inner_radius,
                center[1] + inner_radius,
            ),
            fill=(245, 245, 245),
            outline=(30, 30, 30),
            width=3,
        )

        _draw_centered_text(draw, center, "SPIN", base_font, (0, 0, 0))
        draw.polygon(
            [
                (center[0], pointer_y),
                (center[0] - 14, pointer_y - 30),
                (center[0] + 14, pointer_y - 30),
            ],
            fill=(255, 255, 255),
            outline=(20, 20, 20),
        )

        footer = f"{spinner_name} spun {min_value}-{max_value}"
        _draw_centered_text(draw, (center[0], height - 24), footer, base_font, (230, 230, 230))
        frames.append(img)

    hold_frames = 8
    if frames:
        last_frame = frames[-1]
        for _ in range(hold_frames):
            frames.append(last_frame.copy())

    durations = [45] * len(frames)
    for i in range(max(0, len(frames) - hold_frames), len(frames)):
        durations[i] = 140

    output = io.BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    output.seek(0)
    return output


def _draw_die(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
    value: int,
    wobble: float = 0.0,
):
    # Pseudo-3D cube projection with top and right faces.
    depth = max(6, int(size * (0.18 + 0.06 * wobble)))
    front_x = x
    front_y = y + depth
    front_w = size - depth
    front_h = size - depth

    # Soft shadow under the cube improves depth perception.
    shadow_pad = max(2, depth // 2)
    draw.ellipse(
        (
            front_x + shadow_pad,
            front_y + front_h - shadow_pad,
            front_x + front_w + depth,
            front_y + front_h + shadow_pad,
        ),
        fill=(12, 12, 14),
    )

    top_face = [
        (front_x, front_y),
        (front_x + depth, front_y - depth),
        (front_x + front_w + depth, front_y - depth),
        (front_x + front_w, front_y),
    ]
    right_face = [
        (front_x + front_w, front_y),
        (front_x + front_w + depth, front_y - depth),
        (front_x + front_w + depth, front_y + front_h - depth),
        (front_x + front_w, front_y + front_h),
    ]

    draw.polygon(top_face, fill=(252, 252, 252), outline=(46, 46, 50))
    draw.polygon(right_face, fill=(215, 215, 220), outline=(46, 46, 50))
    draw.rounded_rectangle(
        (front_x, front_y, front_x + front_w, front_y + front_h),
        radius=10,
        fill=(238, 238, 242),
        outline=(28, 28, 30),
        width=2,
    )

    pip_map = {
        1: [(0, 0)],
        2: [(-1, -1), (1, 1)],
        3: [(-1, -1), (0, 0), (1, 1)],
        4: [(-1, -1), (1, -1), (-1, 1), (1, 1)],
        5: [(-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)],
        6: [(-1, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (1, 1)],
    }

    if 1 <= value <= 6:
        step_x = front_w // 4
        step_y = front_h // 4
        radius = max(3, front_w // 12)
        cx = front_x + front_w // 2
        cy = front_y + front_h // 2
        for px, py in pip_map[value]:
            px_abs = cx + px * step_x
            py_abs = cy + py * step_y
            draw.ellipse(
                (px_abs - radius, py_abs - radius, px_abs + radius, py_abs + radius),
                fill=(18, 18, 18),
            )
    else:
        font = ImageFont.load_default()
        _draw_centered_text(
            draw,
            (front_x + front_w // 2, front_y + front_h // 2),
            str(value),
            font,
            (25, 25, 25),
        )


def build_dice_roll_gif(
    dice_count: int,
    dice_sides: int,
    final_rolls: list[int],
    additive_modifier: float,
    multiplier: float,
    spinner_name: str,
) -> io.BytesIO:
    width, height = 620, 360
    frames: list[Image.Image] = []
    frame_count = 28
    font = ImageFont.load_default()

    shown_dice = min(dice_count, 8)

    for frame_index in range(frame_count):
        img = Image.new("RGB", (width, height), (22, 25, 31))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle((16, 16, width - 16, height - 16), radius=22, fill=(34, 39, 49), outline=(70, 78, 95), width=2)
        _draw_centered_text(
            draw,
            (width // 2, 38),
            f"{spinner_name} rolled ({dice_count}d{dice_sides} x {multiplier:g} + {additive_modifier:+g})",
            font,
            (238, 238, 238),
        )

        if frame_index < frame_count - 1:
            current_rolls = [random.randint(1, dice_sides) for _ in range(dice_count)]
        else:
            current_rolls = final_rolls

        cols = 4 if shown_dice > 4 else shown_dice
        rows = (shown_dice + cols - 1) // cols if cols > 0 else 1
        die_size = 62
        grid_w = cols * die_size + (cols - 1) * 14
        grid_h = rows * die_size + (rows - 1) * 14
        start_x = (width - grid_w) // 2
        start_y = 84

        for i in range(shown_dice):
            r = i // cols
            c = i % cols
            x = start_x + c * (die_size + 14)
            y = start_y + r * (die_size + 14)
            wobble = 0.0 if frame_index == frame_count - 1 else math.sin((frame_index + i) * 0.6)
            _draw_die(draw, x, y, die_size, current_rolls[i], wobble=wobble)

        if dice_count > shown_dice:
            _draw_centered_text(
                draw,
                (width // 2, start_y + grid_h + 18),
                f"...and {dice_count - shown_dice} more dice",
                font,
                (210, 210, 210),
            )

        current_base = sum(current_rolls)
        current_modified = current_base * multiplier
        current_total = round(current_modified + additive_modifier, 2)
        _draw_centered_text(draw, (width // 2, height - 70), f"Base sum: {current_base}", font, (242, 242, 242))
        _draw_centered_text(
            draw,
            (width // 2, height - 58),
            f"Total: {current_total:.2f}",
            font,
            (255, 210, 120) if frame_index == frame_count - 1 else (242, 242, 242),
        )

        frames.append(img)

    hold_frames = 8
    if frames:
        last_frame = frames[-1]
        for _ in range(hold_frames):
            frames.append(last_frame.copy())

    durations = [50] * len(frames)
    for i in range(max(0, len(frames) - hold_frames), len(frames)):
        durations[i] = 140

    output = io.BytesIO()
    frames[0].save(
        output,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
    output.seek(0)
    return output


async def process_external_send_event(
    guild: discord.Guild | None,
    user_id: int,
    amount: float,
    source: str,
    princess_user_id: int | None = None,
) -> dict | None:
    if guild is None:
        return None
    member = guild.get_member(user_id)
    if member is None:
        return None
    princess_member = None
    if princess_user_id is not None:
        princess_member = guild.get_member(princess_user_id)
        if princess_member is None:
            try:
                princess_member = await guild.fetch_member(princess_user_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                princess_member = None
    return await register_send_event(member, amount, source, princess_member=princess_member)
