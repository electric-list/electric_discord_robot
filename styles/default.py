"""
Default style — preserves all original strings from the initial bot implementation.
Switch back to this with: {"active_style": "default"} in style_config.json
"""

from styles import StylePack

kit = StylePack(
    name="Default",

    # ── Jokes ─────────────────────────────────────────────────────────────────
    jokes=[
        "Why did the simp go to the bank? To get a new debit card because the old one was worn out from paying someone's coffee.",
        "My wallet tried to file a missing person report. Apparently I keep sending it away.",
        "I asked for financial advice and my bank app just replied: 'Again?'",
        "Promotion at work? Great, now my tribute budget can finally breathe.",
        "The princess said 'touch grass' so I bought premium turf and sent the receipt.",
        "My spending tracker renamed itself to 'devotion analytics'.",
        "I don't chase people anymore. I just chase payment confirmations.",
        "My card declined once, and now it apologizes before every purchase.",
        "I said I was done simping. Then payday loaded and I got amnesia.",
        "My love language is direct deposit.",
        "Friends asked if I have hobbies. I said yes, recurring transactions.",
        "I wanted to be independent, but then I saw a command button that said 'I Sent'.",
        "Even my calculator says, 'At this point, this is a subscription.'",
        "I tried budgeting, but my spreadsheet labeled everything as 'for princess'.",
        "My bank statement reads like a fan page.",
        "I don't need small talk. I need a payment link.",
        "Every time I say 'just one send', my wallet laughs.",
        "The simp life chose me right after my paycheck hit.",
    ],

    # ── Rank-up ───────────────────────────────────────────────────────────────
    rank_up_messages=[
        "{mention} just got a bigger simp for me 💸",
        "Omg {mention} is climbing the ranks, keep sending 💅",
        "{mention} just leveled up their devotion 💗",
        "Look who just proved they're more than a little simp 👑 {mention}",
        "{mention} just unlocked a new title — keep spoiling me 🎀",
    ],
    rank_up_tier_change="{old} → {new}",

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_record_send="Record Send",
    btn_delete_message="Delete Message",
    btn_i_sent="I Sent",
    btn_delete_request="Delete",
    btn_approve_claim="Approve and Record",
    btn_delete_claim="Delete Request",
    btn_refresh_leaderboard="Refresh",

    # ── Modal ─────────────────────────────────────────────────────────────────
    modal_send_proof_title="Confirm Send for Request",
    modal_amount_label="Amount Sent",
    modal_amount_placeholder="e.g., 100.00",
    modal_note_label="Note (optional)",
    modal_note_placeholder="Optional note",
    modal_platform_label="Platform",
    modal_platform_placeholder="e.g., wishtender, throne, cashapp",

    # ── Tribute / record result templates ─────────────────────────────────────
    tpl_tribute_positive="{mention} sent :money_with_wings: ${amount:.2f} :money_with_wings:{source_suffix}!",
    tpl_tribute_negative="Adjusted {mention} by -${adj_amount:.2f}{source_suffix}. Removed ${removed_amount:.2f} from recent sends.",
    tpl_tribute_negative_remainder="${remaining:.2f} could not be applied because there were not enough recorded sends.",
    tpl_tribute_negative_rank="Current rank: {rank}",
    tpl_tribute_role_warning="⚠️ Could not assign rank role — the bot's role may need to be moved higher in the server role list.",

    # ── Approval templates ────────────────────────────────────────────────────
    tpl_approval_reimburse="{mention} reimbursed {item} with a ${amount:.2f} send via {platform}!",
    tpl_approved_by="\n-# Approved by {approver}.",

    # ── Game source labels ────────────────────────────────────────────────────
    tpl_game_source_dice="\nFrom dice roll.",
    tpl_game_source_wheelspin="\nFrom wheel spin.",

    # ── Request / sub-sent templates ──────────────────────────────────────────
    tpl_request_send="{mention} requests a send of {amount:.2f}{target_text}.{note_text}",
    tpl_request_reimburse="{mention} requests a reimbursement of {amount:.2f} for {item}{target_text}.{note_text}",
    tpl_sub_sent="{mention} says they sent {amount:.2f} via {platform} and requests registration.{note_text}",
    tpl_claim_sent="{mention} says they sent {amount:.2f} via {platform}{request_context}.{proof_text}",
    tpl_claim_reimburse="{mention} says they reimbursed {item} with a {amount:.2f} send via {platform}{request_context}.{proof_text}",

    # ── Game result templates ─────────────────────────────────────────────────
    tpl_dice_result="{mention} rolled **({formula})** for {princess_mention}. Base **{base_sum}** -> final **{total:.2f}**",
    tpl_wheel_result="{mention} spun the wheel for {princess_mention} and landed on **{result}**.",

    # ── Progress embed ────────────────────────────────────────────────────────
    embed_progress_color=0xFAA61A,      # discord gold
    embed_progress_title="Progression: {name}",
    embed_progress_field_rank="Rank",
    embed_progress_field_total="Total Sent",
    embed_progress_field_avg="Avg Weekly",
    embed_progress_field_count="Send Count",
    embed_progress_footer="Level role is based on average weekly sends",

    # ── Leaderboard embed ─────────────────────────────────────────────────────
    embed_leaderboard_color=0x5865F2,   # discord blurple
    embed_leaderboard_title="Leaderboard by {metric_label} ({period_suffix})",
    embed_leaderboard_metric_total="Total Sent",
    embed_leaderboard_metric_avg="Avg Weekly",
    embed_leaderboard_row="{index}. {member_display} - {value:.2f}",
)
