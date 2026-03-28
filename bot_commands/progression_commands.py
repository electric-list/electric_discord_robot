import discord
from discord import app_commands
from datetime import date, timedelta
import calendar

import bot_core as core
import styles


ACCESS_GROUP_CHOICES = [
    app_commands.Choice(name="Admin Roles", value="admin"),
    app_commands.Choice(name="Common Roles", value="common"),
]


def _group_label(group: str) -> str:
    return "Admin" if group == "admin" else "Common"


def _format_role_mentions(role_ids: list[int]) -> str:
    if not role_ids:
        return "(none)"
    return " ".join(f"<@&{role_id}>" for role_id in role_ids)


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _period_bounds(period_key: str, anchor_day: date) -> tuple[date | None, date | None]:
    if period_key == "all":
        return None, anchor_day
    if period_key == "week":
        start = core.week_start(anchor_day)
        end = start + timedelta(days=6)
        return start, end
    if period_key == "month":
        start = anchor_day.replace(day=1)
        month_days = calendar.monthrange(anchor_day.year, anchor_day.month)[1]
        end = anchor_day.replace(day=month_days)
        return start, end
    return None, anchor_day


def _events_in_range(stats: dict, start_day: date | None, end_day: date | None) -> list[dict]:
    history = stats.get("send_history", [])
    if not isinstance(history, list):
        return []

    collected: list[dict] = []
    for event in history:
        if not isinstance(event, dict):
            continue
        event_date_raw = event.get("date")
        if not isinstance(event_date_raw, str):
            continue
        try:
            event_day = date.fromisoformat(event_date_raw)
        except ValueError:
            continue

        if start_day is not None and event_day < start_day:
            continue
        if end_day is not None and event_day > end_day:
            continue
        collected.append(event)
    return collected


def _event_matches_princess(event: dict, princess_user_id: int | None) -> bool:
    if princess_user_id is None:
        return True
    raw = event.get("princess_user_id")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return False
    return value == int(princess_user_id)


def _leaderboard_value_for_period(
    stats: dict,
    metric_key: str,
    period_key: str,
    period_start: date | None,
    period_end: date | None,
    princess_user_id: int | None = None,
) -> float:
    if period_key == "all" and period_end is None:
        if princess_user_id is None:
            return float(core.leaderboard_metric_value(stats, metric_key, "all"))

    events = [
        event
        for event in _events_in_range(stats, period_start, period_end)
        if _event_matches_princess(event, princess_user_id)
    ]
    total = round(sum(float(event.get("amount", 0.0)) for event in events), 2)
    if metric_key == "total_sent":
        return total

    if period_key == "all":
        if not events:
            return 0.0
        dated_events = []
        for event in events:
            event_date_raw = event.get("date")
            if isinstance(event_date_raw, str):
                try:
                    dated_events.append(date.fromisoformat(event_date_raw))
                except ValueError:
                    pass
        if not dated_events:
            return 0.0
        first_week_start = core.week_start(min(dated_events))
        end_day = period_end or date.today()
        elapsed_weeks = ((end_day - first_week_start).days // 7) + 1
        elapsed_weeks = max(1, elapsed_weeks)
        return round(total / elapsed_weeks, 2)

    if period_start is None or period_end is None:
        return total

    # Convert period length to effective weeks so month values scale by actual days.
    span_days = (period_end - period_start).days + 1
    effective_weeks = max(span_days / 7.0, 1.0)
    return round(total / effective_weeks, 2)


def _period_title_suffix(period_key: str, period_start: date | None) -> str:
    if period_key == "week" and period_start is not None:
        return f"Week of {period_start.isoformat()}"
    if period_key == "month" and period_start is not None:
        return period_start.strftime("%B %Y")
    return "All Time"


def _in_refresh_window(period_key: str, period_end: date | None, today: date) -> bool:
    if period_key == "all":
        return True
    if period_end is None:
        return False
    if period_key == "week":
        return today >= (period_end - timedelta(days=1)) and today <= period_end
    if period_key == "month":
        return today >= (period_end - timedelta(days=2)) and today <= period_end
    return False


def register_progression_commands(client, admin_group_getter, common_group_getter):
    async def autocomplete_princess_members(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        if interaction.guild is None:
            return []

        princess_role_id = core.get_princess_role_id()
        if princess_role_id is None:
            return []

        role = interaction.guild.get_role(princess_role_id)
        if role is None:
            return []

        current_lower = current.lower()
        choices: list[app_commands.Choice[str]] = []
        for member in role.members:
            if current_lower and current_lower not in member.display_name.lower() and current_lower not in member.name.lower():
                continue
            choices.append(app_commands.Choice(name=member.display_name[:100], value=str(member.id)))
        return choices[:25]

    async def send_tribute_result(interaction: discord.Interaction, message: str):
        tributes_channel = (
            core.resolve_tributes_channel(interaction.guild)
            if interaction.guild is not None
            else None
        )
        current_channel_id = getattr(interaction.channel, "id", None)

        if tributes_channel is not None and tributes_channel.id == current_channel_id:
            await interaction.response.send_message(message)
            return

        await core.post_tributes_message(interaction.guild, message)
        await interaction.response.send_message(message, ephemeral=True)

    
    @client.tree.command(
        name="recordsend", description="Record a send and update progression/rank"
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(
        member="The member who sent",
        amount="Positive to add a send, negative to remove from recent sends",
        source="Source system (finbot, throne, manual, youpay)",
    )
    async def recordsend(
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[float, -1000000.0, 1000000.0],
        source: str = "manual",
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Could not resolve member.", ephemeral=True)
            return

        if float(amount) == 0.0:
            await interaction.response.send_message(
                "Amount cannot be 0.", ephemeral=True
            )
            return
        result = await core.register_send_event(
            member,
            float(amount),
            source,
            princess_member=interaction.user,
        )
        message = core.format_record_result(member, float(amount), source, result)
        await send_tribute_result(interaction, message)

    @client.tree.command(
        name="progress", description="Show progression profile for yourself or another member"
    )
    @core.require_any_role(common_group_getter)
    @app_commands.describe(
        member="Leave empty to view your own profile",
        public="If true, post in channel. If false, only you can see it",
    )
    async def progress(
        interaction: discord.Interaction,
        member: discord.Member | None = None,
        public: bool = False,
    ):
        requester = interaction.user
        if not isinstance(requester, discord.Member):
            await interaction.response.send_message(
                "Could not resolve requesting member.", ephemeral=True
            )
            return

        target = member or interaction.user
        if not isinstance(target, discord.Member):
            await interaction.response.send_message(
                "Could not resolve member.", ephemeral=True
            )
            return

        requester_has_common = core.has_any_role_id(requester, common_group_getter())
        requester_has_admin = core.has_any_role_id(requester, admin_group_getter())
        if requester_has_common and not requester_has_admin and target.id != requester.id:
            await interaction.response.send_message(
                "Common-role members can only view their own progress.",
                ephemeral=True,
            )
            return

        data = core.load_stats()
        stats = core.get_user_stats_blob(data, target.id)
        rank_role_id_str = core.rank_for_stats(stats)
        rank_role_id = int(rank_role_id_str) if rank_role_id_str else 0
        avg_weekly = core.avg_weekly_for_stats(stats, "all")

        rank_display = f"<@&{rank_role_id}>" if rank_role_id > 0 else "Unranked"

        kit = styles.get()
        embed = discord.Embed(
            title=kit.embed_progress_title.format(name=target.display_name),
            color=discord.Color(kit.embed_progress_color),
        )
        embed.add_field(name=kit.embed_progress_field_rank, value=rank_display, inline=True)
        embed.add_field(
            name=kit.embed_progress_field_total,
            value=f"{float(stats.get('total_sent', 0.0)):.2f}",
            inline=True,
        )
        embed.add_field(name=kit.embed_progress_field_avg, value=f"{avg_weekly:.2f}", inline=True)
        embed.add_field(
            name=kit.embed_progress_field_count, value=str(stats.get("send_count", 0)), inline=True
        )
        embed.set_footer(text=kit.embed_progress_footer)

        await interaction.response.send_message(embed=embed, ephemeral=not public)

    @client.tree.command(
        name="sendleaderboard", description="Leaderboard by metric and period"
    )
    @core.require_any_role(common_group_getter)
    @app_commands.describe(
        metric="How to sort the leaderboard",
        period="Time period",
        target_date="Optional date in YYYY-MM-DD to view a past snapshot",
        princess="Optional: only include sends for one princess",
        public="If true, post publicly (admin only). Otherwise private.",
    )
    @app_commands.choices(
        metric=[
            app_commands.Choice(name="Total Sent", value="total_sent"),
            app_commands.Choice(name="Avg Weekly", value="avg_weekly"),
        ],
        period=[
            app_commands.Choice(name="This Week", value="week"),
            app_commands.Choice(name="This Month", value="month"),
            app_commands.Choice(name="All Time", value="all"),
        ],
    )
    @app_commands.autocomplete(princess=autocomplete_princess_members)
    async def sendleaderboard(
        interaction: discord.Interaction,
        metric: app_commands.Choice[str] | None = None,
        period: app_commands.Choice[str] | None = None,
        target_date: str | None = None,
        princess: str | None = None,
        public: bool = False,
    ):
        chosen_metric = metric.value if metric else "total_sent"
        chosen_period = period.value if period else "all"
        requester = interaction.user
        requester_is_admin = isinstance(requester, discord.Member) and core.has_any_role_id(requester, admin_group_getter())
        response_ephemeral = not (public and requester_is_admin)

        princess_member = None
        if princess:
            try:
                princess_id = int(princess)
            except (TypeError, ValueError):
                await interaction.response.send_message("Please select a valid princess.", ephemeral=True)
                return

            guild = interaction.guild
            princess_member = guild.get_member(princess_id) if guild is not None else None
            if princess_member is None and guild is not None:
                try:
                    princess_member = await guild.fetch_member(princess_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    princess_member = None

            if princess_member is None or not core.is_princess_member(princess_member):
                await interaction.response.send_message("Please select a valid princess.", ephemeral=True)
                return

        custom_day = None
        if target_date:
            custom_day = _parse_iso_date(target_date)
            if custom_day is None:
                await interaction.response.send_message(
                    "Invalid date format. Use YYYY-MM-DD.", ephemeral=True
                )
                return

        anchor_day = custom_day or date.today()
        period_start, period_end = _period_bounds(chosen_period, anchor_day)
        today = date.today()
        period_has_passed = period_end is not None and period_end < today

        async def build_embed_for(i: discord.Interaction) -> discord.Embed | None:
            data = core.load_stats()
            users = data.get("users", {})

            rows = []
            for user_id_str, stats in users.items():
                try:
                    user_id = int(user_id_str)
                except ValueError:
                    continue

                mention_or_name = stats.get("display_name") or f"User {user_id}"
                if i.guild:
                    member = i.guild.get_member(user_id)
                    if member is None:
                        try:
                            member = await i.guild.fetch_member(user_id)
                        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                            member = None
                    if member is not None:
                        mention_or_name = member.mention

                metric_value = _leaderboard_value_for_period(
                    stats,
                    chosen_metric,
                    chosen_period,
                    period_start,
                    period_end,
                    princess_member.id if princess_member is not None else None,
                )
                rows.append((mention_or_name, metric_value))

            if not rows:
                return None

            rows.sort(key=lambda row: row[1], reverse=True)
            top_rows = rows[:10]

            kit = styles.get()
            metric_label = {
                "total_sent": kit.embed_leaderboard_metric_total,
                "avg_weekly": kit.embed_leaderboard_metric_avg,
            }.get(chosen_metric, kit.embed_leaderboard_metric_total)

            period_suffix = _period_title_suffix(chosen_period, period_start)
            if chosen_period == "all" and custom_day is not None:
                period_suffix = f"All Time through {custom_day.isoformat()}"
            if princess_member is not None:
                period_suffix = f"{period_suffix} • For {princess_member.display_name}"

            leaderboard_lines = []
            for index, (member_display, metric_value) in enumerate(top_rows, start=1):
                leaderboard_lines.append(
                    kit.embed_leaderboard_row.format(
                        index=index,
                        member_display=member_display,
                        value=float(metric_value),
                    )
                )

            embed = discord.Embed(
                title=kit.embed_leaderboard_title.format(
                    metric_label=metric_label,
                    period_suffix=period_suffix,
                ),
                description="\n".join(leaderboard_lines),
                color=discord.Color(kit.embed_leaderboard_color),
            )
            if chosen_period in {"week", "month"} and period_has_passed and period_end is not None:
                embed.set_footer(text=f"Frozen at period end: {period_end.isoformat()}")
            elif custom_day is not None:
                embed.set_footer(text=f"Snapshot date: {custom_day.isoformat()}")
            return embed

        class LeaderboardRefreshView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=900)
                kit = styles.get()
                for child in self.children:
                    if isinstance(child, discord.ui.Button):
                        child.label = kit.btn_refresh_leaderboard

            @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary)
            async def refresh(self, button_interaction: discord.Interaction, _button: discord.ui.Button):
                refreshed_embed = await build_embed_for(button_interaction)
                if refreshed_embed is None:
                    await button_interaction.response.send_message(
                        "No progression data yet.", ephemeral=True
                    )
                    return
                await button_interaction.response.edit_message(embed=refreshed_embed, view=self)

        embed = await build_embed_for(interaction)
        if embed is None:
            await interaction.response.send_message(
                "No progression data yet.", ephemeral=True
            )
            return

        await interaction.response.send_message(
            embed=embed,
            view=LeaderboardRefreshView(),
            ephemeral=response_ephemeral,
        )

    @client.tree.command(
        name="ranksync",
        description="Sync rank role for one member, or all tracked members if none given",
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(member="Leave empty to sync all tracked members")
    async def ranksync(interaction: discord.Interaction, member: discord.Member | None = None):
        if interaction.guild is None:
            await interaction.response.send_message("Guild not available.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if member is not None:
            data = core.load_stats()
            stats = core.get_user_stats_blob(data, member.id)
            core.save_stats(data)
            previous_rank_ids = core.get_member_rank_role_ids(member)
            previous_rank_id = previous_rank_ids[0] if previous_rank_ids else None
            rank_id, _removed, _changed = await core.sync_rank_role(member, stats)
            new_rank_id = int(rank_id) if rank_id else 0
            if new_rank_id and previous_rank_id != new_rank_id:
                try:
                    avg_weekly = core.avg_weekly_for_stats(stats, "all")
                    await core.announce_rank_change(member, previous_rank_id, new_rank_id, 0.0, "ranksync", avg_weekly)
                except Exception:
                    pass
            rank_display = f"<@&{new_rank_id}>" if new_rank_id else "Unranked"
            await interaction.followup.send(
                f"Synced rank for {member.mention}. Current rank: {rank_display}.",
                ephemeral=True,
            )
            return

        data = core.load_stats()
        users = data.get("users", {})
        checked = 0
        updated = 0
        managed_rank_ids = [int(tier["role_id"]) for tier in core.get_rank_tiers()]

        for user_id_str, user_stats in users.items():
            try:
                user_id = int(user_id_str)
            except ValueError:
                continue

            m = interaction.guild.get_member(user_id)
            if m is None:
                try:
                    m = await interaction.guild.fetch_member(user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    m = None
            if m is None:
                continue

            checked += 1
            normalized_stats = core.normalize_user_stats_shape(user_stats)
            target_rank = core.rank_for_stats(normalized_stats)
            previous_ranks = core.get_member_rank_role_ids(m)
            previous_rank_id = previous_ranks[0] if previous_ranks else None
            await core.sync_rank_role(m, normalized_stats)
            target_rank_id = int(target_rank) if target_rank else 0
            current_rank_ids = core.get_member_rank_role_ids(m)
            if target_rank_id and previous_rank_id != target_rank_id:
                updated += 1
                try:
                    avg_weekly = core.avg_weekly_for_stats(normalized_stats, "all")
                    await core.announce_rank_change(m, previous_rank_id, target_rank_id, 0.0, "ranksync", avg_weekly)
                except Exception:
                    pass
            elif set(previous_ranks) != set(current_rank_ids):
                updated += 1

        core.save_stats(data)
        await interaction.followup.send(
            f"Synced ranks for {checked} tracked member(s). Updated role state for {updated} member(s).",
            ephemeral=True,
        )

    async def autocomplete_recent_sends(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        cutoff = date.today() - timedelta(days=3)
        data = core.load_stats()
        users = data.get("users", {})

        entries: list[tuple[date, str, app_commands.Choice[str]]] = []
        for user_id_str, stats in users.items():
            history = stats.get("send_history", [])
            if not isinstance(history, list):
                continue
            display_name = stats.get("display_name") or f"User {user_id_str}"
            for idx, event in enumerate(history):
                if not isinstance(event, dict):
                    continue
                date_raw = event.get("date", "")
                try:
                    event_day = date.fromisoformat(date_raw)
                except ValueError:
                    continue
                if event_day < cutoff:
                    continue
                amount = float(event.get("amount", 0.0))
                label = f"{display_name} | {amount:.2f} | {date_raw}"
                if current.lower() not in label.lower():
                    continue
                value = f"{user_id_str}:{idx}:{date_raw}:{amount:.2f}"
                entries.append((event_day, date_raw, app_commands.Choice(name=label[:100], value=value)))

        entries.sort(key=lambda e: e[0], reverse=True)
        return [c for _, _, c in entries[:25]]

    @client.tree.command(name="removesend", description="Remove a recorded send")
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(send="Select a recent send to remove")
    @app_commands.autocomplete(send=autocomplete_recent_sends)
    async def removesend(interaction: discord.Interaction, send: str):
        try:
            user_id_str, idx_str, event_date, amount_str = send.split(":", 3)
            user_id = int(user_id_str)
            event_index = int(idx_str)
            expected_amount = float(amount_str)
        except (ValueError, AttributeError):
            await interaction.response.send_message("Invalid selection.", ephemeral=True)
            return

        success, updated_stats, removed_amount = core.remove_send_event(
            user_id,
            event_index,
            expected_date=event_date,
            expected_amount=expected_amount,
        )
        if not success:
            await interaction.response.send_message(
                "Could not find that send. It may have already been removed.", ephemeral=True
            )
            return

        current_rank_display = "Unranked"
        member = None
        if interaction.guild is not None and updated_stats is not None:
            member = interaction.guild.get_member(user_id)
            if member is None:
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    member = None

            if member is not None:
                rank_id, _removed, _changed = await core.sync_rank_role(member, updated_stats)
                current_rank_display = f"<@&{int(rank_id)}>" if rank_id else "Unranked"

        removed_display = f"${float(removed_amount or 0.0):.2f}"
        if member is not None:
            target_display = member.mention
        elif updated_stats is not None and updated_stats.get("display_name"):
            target_display = str(updated_stats["display_name"])
        else:
            target_display = f"user {user_id}"
        message = f"Removed send of {removed_display} from {target_display} successfully. Current rank: {current_rank_display}."
        await send_tribute_result(interaction, message)

    return {
        "recordsend": recordsend,
        "progress": progress,
        "sendleaderboard": sendleaderboard,
        "ranksync": ranksync,
        "removesend": removesend,
    }
