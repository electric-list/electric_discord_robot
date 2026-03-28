"""
Style system for Jordan's Robot.

A StylePack defines all user-facing text, button labels, and embed config.
Create a new style file under styles/ that assigns a `kit = StylePack(...)` instance,
then set `{"active_style": "your_style_name"}` in style_config.json to activate it.
"""

import importlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_style_config_file = Path("style_config.json")
_active_kit: Optional["StylePack"] = None
TemplateOrPool = str | list[str]


@dataclass
class StylePack:
    # ── Meta ─────────────────────────────────────────────────────────────────
    name: str  # Display name for the style

    # ── Content arrays ────────────────────────────────────────────────────────
    jokes: list                     # Random joke pool for /telljoke
    rank_up_messages: list          # Rank-up announcement pool; placeholder: {mention}
    rank_up_tier_change: str        # Tier-change line; placeholders: {old}, {new}

    # ── Button labels ─────────────────────────────────────────────────────────
    btn_record_send: str
    btn_delete_message: str
    btn_i_sent: str
    btn_delete_request: str         # "Delete" button on RequestView
    btn_approve_claim: str
    btn_delete_claim: str           # "Delete" button on SubSendClaimView
    btn_refresh_leaderboard: str

    # ── SendProofModal ─────────────────────────────────────────────────────────
    modal_send_proof_title: str
    modal_amount_label: str
    modal_amount_placeholder: str
    modal_note_label: str
    modal_note_placeholder: str
    modal_platform_label: str
    modal_platform_placeholder: str

    # ── Message templates (use str.format(**kwargs)) ───────────────────────────
    # format_record_result — used by /recordsend and game Record button
    tpl_tribute_positive: TemplateOrPool    # {mention} {amount:.2f} {source_suffix}
    tpl_tribute_negative: str           # {mention} {adj_amount:.2f} {source_suffix} {removed_amount:.2f}
    tpl_tribute_negative_remainder: str # {remaining:.2f}
    tpl_tribute_negative_rank: str      # {rank}
    tpl_tribute_role_warning: str       # (no placeholders)

    # SubSendClaimView approve — reimbursement-specific message
    tpl_approval_reimburse: TemplateOrPool  # {mention} {amount:.2f} {platform} {item}

    # Approved-by suffix appended to approval tributes messages
    tpl_approved_by: str                # {approver}
    tpl_noted_for: str                  # {princess}

    # Source labels appended after game Record button tribute message
    tpl_game_source_dice: str           # prepended \n, no placeholders
    tpl_game_source_wheelspin: str      # prepended \n, no placeholders

    # /requestsend public message
    tpl_request_send: str               # {mention} {amount:.2f} {target_text} {note_text}
    tpl_request_reimburse: str          # {mention} {amount:.2f} {item} {target_text} {note_text}

    # /iamasubandisent public message
    tpl_sub_sent: str                   # {mention} {amount:.2f} {platform} {note_text}

    # SendProofModal claim messages (sent from "I Sent" button)
    tpl_claim_sent: str                 # {mention} {amount:.2f} {platform} {request_context} {proof_text}
    tpl_claim_reimburse: str            # {mention} {amount:.2f} {platform} {item} {request_context} {proof_text}

    # /dice and /wheelspin result messages
    tpl_dice_result: str                # {mention} {formula} {base_sum} {total:.2f}
    tpl_wheel_result: str               # {mention} {result}

    # ── Progress embed ────────────────────────────────────────────────────────
    embed_progress_color: int           # Hex int, e.g. 0xFFB6C1
    embed_progress_title: str           # {name}
    embed_progress_field_rank: str      # Field label
    embed_progress_field_total: str     # Field label
    embed_progress_field_avg: str       # Field label
    embed_progress_field_count: str     # Field label
    embed_progress_footer: str

    # ── Leaderboard embed ─────────────────────────────────────────────────────
    embed_leaderboard_color: int        # Hex int
    embed_leaderboard_title: str        # {metric_label} {period_suffix}
    embed_leaderboard_metric_total: str # Display label for "total_sent" metric
    embed_leaderboard_metric_avg: str   # Display label for "avg_weekly" metric
    embed_leaderboard_row: str          # {index} {member_display} {value:.2f}


def load(style_name: str) -> "StylePack":
    """Import styles.<style_name>, set it as the active kit, and return it."""
    global _active_kit
    mod = importlib.import_module(f"styles.{style_name}")
    _active_kit = mod.kit
    return _active_kit


def get() -> "StylePack":
    """Return the currently active StylePack. Raises if none is loaded."""
    if _active_kit is None:
        raise RuntimeError("No style loaded. Call styles.load_from_config() before accessing styles.")
    return _active_kit


def choose_template(template_or_pool: TemplateOrPool) -> str:
    """Return one template string, choosing randomly when a non-empty list is provided."""
    if isinstance(template_or_pool, list):
        if not template_or_pool:
            raise ValueError("Template pool cannot be empty.")
        return random.choice(template_or_pool)
    return template_or_pool


def render_template(template_or_pool: TemplateOrPool, **kwargs) -> str:
    """Render either a single template string or a random template from a pool."""
    return choose_template(template_or_pool).format(**kwargs)


def load_from_config() -> "StylePack":
    """
    Read style_config.json and load the specified style.
    Falls back to 'default' if the file is missing, unreadable, or the style fails to import.
    """
    style_name = "default"
    if _style_config_file.exists():
        try:
            data = json.loads(_style_config_file.read_text(encoding="utf-8"))
            style_name = str(data.get("active_style", "default"))
        except Exception:
            pass
    try:
        return load(style_name)
    except Exception:
        if style_name != "default":
            return load("default")
        raise
