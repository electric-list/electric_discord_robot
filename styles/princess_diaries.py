"""
The Princess Diaries style — cute, princessy, and lightly triggering for subs.
Theme: entitled princess energy 👑, sparkles ✨, and playful condescension 💅.

Switch to this with: {"active_style": "princess_diaries"} in style_config.json
"""

from styles import StylePack

kit = StylePack(
    name="The Princess Diaries",

    # ── Jokes ─────────────────────────────────────────────────────────────────
    jokes=[
        "Why does a simp check their bank account every morning? To see how much devotion they have left. 💸",
        "My sub said 'sorry for the late tribute'. I said I don't accept apologies — I accept late fees. 👑",
        "The WiFi password is one sent tribute per character. Good luck. 💅",
        "A sub asked me what I want for my birthday. I handed him a payment link. 🎂",
        "My sub said he's trying to find himself. I said try looking in your bank app under recent transactions. 💳",
        "They say love is priceless. Cute theory. Open your wallet. 💸",
        "My sub asked if I love him. I said I love what he does. He smiled. I meant the tributes. 🎀",
        "A simp's favorite fantasy is being financially useful. Dream responsibly. 💅",
        "I asked my sub for a gift. He asked what I wanted. I said start with your dignity and work up from there. 👑",
        "My sub said he'd walk through fire for me. I said the payment portal only requires a card number. 💳",
        "Why do subs love princesses? Something about 'serve and protect'. Mostly serve. 💸",
        "My bank account is basically a group chat — it only gets interesting when subs check in. 📱",
        "He said he'd do anything for me. I opened the tribute page. He said 'within reason'. Cute. 💅",
        "My sub asked if I think about him. I said yes, usually when payday hits and I check my balance. 👑",
        "Love is patient. Love is kind. Love is also a tribute of at least $30. 💗",
        "I don't keep receipts out of sentimentality. I keep them for tax purposes. 💳",
        "My sub learned the word 'boundary' and then forgot it the moment I posted a wishlist. 🎀",
        "The princess life chose me. The tribute life chose you. We both got what we deserved. 💸",
    ],

    # ── Rank-up ───────────────────────────────────────────────────────────────
    rank_up_messages=[
        "{mention} just proved they're slightly less disappointing 💅 The court acknowledges.",
        "Oh? {mention} is actually stepping up? How... expected. But appreciated. 👑",
        "✨ {mention} has ascended to a new rank! The Princess is briefly impressed.",
        "Look who finally unlocked a better title — {mention}! Don't let it go to your wallet. 💗",
        "{mention} just earned a higher rank. Adorable effort 🎀 Keep sending.",
        "The Princess has noticed {mention} climbing the ranks. Try harder. 💅",
        "✨ Oh, a new rank for {mention}! The Princess is... mildly pleased. Maybe.",
    ],
    rank_up_tier_change="{old} ✦ {new}",

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_record_send="✅ Record Tribute",
    btn_delete_message="🗑️ Delete",
    btn_i_sent="💸 I Sent, Princess",
    btn_delete_request="🗑️ Delete",
    btn_approve_claim="👑 Approve Tribute",
    btn_delete_claim="🗑️ Delete",
    btn_refresh_leaderboard="✨ Refresh",

    # ── Modal ─────────────────────────────────────────────────────────────────
    modal_send_proof_title="📋 Tribute Confirmation",
    modal_amount_label="How much did you send, little one?",
    modal_amount_placeholder="e.g., 100.00",
    modal_note_label="Anything to confess?",
    modal_note_placeholder="Optional note",
    modal_platform_label="Where did you send?",
    modal_platform_placeholder="e.g., wishtender, throne, cashapp",

    # ── Tribute / record result templates ─────────────────────────────────────
    tpl_tribute_positive="💸 {mention} sent **${amount:.2f}**{source_suffix} into the simp tax jar! The Princess accepts 👑",
    tpl_tribute_negative="Adjusted {mention} by -${adj_amount:.2f}{source_suffix}. ${removed_amount:.2f} removed from the loser ledger.",
    tpl_tribute_negative_remainder="${remaining:.2f} could not be applied — not enough recorded sends.",
    tpl_tribute_negative_rank="Current standing: {rank}",
    tpl_tribute_role_warning="⚠️ Could not assign rank role — the bot's role may need to be moved higher in the server role list.",

    # ── Approval templates ────────────────────────────────────────────────────
    tpl_approval_reimburse="💳 {mention} repaid the simp debt — **${amount:.2f}** via **{platform}** for **{item}**! Debt cleared. 💅",
    tpl_approved_by="\n-# 👑 Noted by {approver}.",

    # ── Game source labels ────────────────────────────────────────────────────
    tpl_game_source_dice="\n🎲 From the simp dice roll.",
    tpl_game_source_wheelspin="\n🎡 From the Princess's wheel of fate.",

    # ── Request / sub-sent templates ──────────────────────────────────────────
    tpl_request_send="👑 **Princess Ping**: {mention} requests a tribute of **${amount:.2f}**{target_text}.{note_text}",
    tpl_request_reimburse="💳 **Princess IOU**: {mention} is owed **${amount:.2f}** for **{item}**{target_text}.{note_text}",
    tpl_sub_sent="🙇 {mention} humbly claims to have sent **${amount:.2f}** via **{platform}** and awaits the Princess's acknowledgment.{note_text}",
    tpl_claim_sent="🙇 {mention} says they sent **${amount:.2f}** via **{platform}**{request_context}.{proof_text}",
    tpl_claim_reimburse="💳 {mention} says they reimbursed **{item}** with a **${amount:.2f}** send via **{platform}**{request_context}.{proof_text}",

    # ── Game result templates ─────────────────────────────────────────────────
    tpl_dice_result="🎲 {mention} rolled the simp dice **({formula})**. Base **{base_sum}** → tribute due: **${total:.2f}** 💸",
    tpl_wheel_result="🎡 {mention} spun the loser wheel of fate and owes **${result}** 💅",

    # ── Progress embed ────────────────────────────────────────────────────────
    embed_progress_color=0xFFB6C1,      # light pink
    embed_progress_title="📖 Princess Diary — {name}'s Record",
    embed_progress_field_rank="👑 Simp Rank",
    embed_progress_field_total="💸 Total Tributes",
    embed_progress_field_avg="📅 Weekly Devotion (avg)",
    embed_progress_field_count="🎀 Send Count",
    embed_progress_footer="Level is based on weekly devotion 💗",

    # ── Leaderboard embed ─────────────────────────────────────────────────────
    embed_leaderboard_color=0xFFD700,   # gold
    embed_leaderboard_title="👑 Simp Leaderboard — {metric_label} ({period_suffix})",
    embed_leaderboard_metric_total="Total Tributes",
    embed_leaderboard_metric_avg="Weekly Devotion",
    embed_leaderboard_row="{index}. {member_display} — ${value:.2f}",
)
