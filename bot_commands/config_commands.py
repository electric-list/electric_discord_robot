import discord
from discord import app_commands

import bot_core as core
from backup_google_drive import manager as backup_manager


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


def register_config_commands(client, admin_group_getter, common_group_getter):

    @client.tree.command(
        name="backupnow",
        description="Upload progression_data.json to Google Drive now (for testing)",
    )
    @core.require_any_role(admin_group_getter)
    async def backupnow(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        ok, message = await backup_manager.trigger_backup_now(core.stats_file, force=True)
        
        if not ok and "GDRIVE_CLIENT_SECRET_JSON_PATH" in message:
            setup_msg = (
                f"{message}\n\n**Setup instructions for OAuth 2.0 backups:**\n"
                "1. Go to https://console.cloud.google.com/\n"
                "2. Create a new Google Cloud project\n"
                "3. Enable Google Drive API (APIs & Services > Library > search Drive)\n"
                "4. Go to APIs & Services > Credentials\n"
                "5. Click Create Credentials > OAuth 2.0 Client ID\n"
                "6. Choose Desktop application\n"
                "7. Download JSON and save to your bot folder as `client_secret.json`\n"
                "8. Set env var: `GDRIVE_CLIENT_SECRET_JSON_PATH=./client_secret.json`\n"
                "9. Also set: `GDRIVE_BACKUP_ENABLED=true`\n"
                "10. Run `/backupnow` again — it will open a browser to authorize\n"
            )
            await interaction.followup.send(setup_msg, ephemeral=True)
        else:
            prefix = "Backup completed." if ok else "Backup test failed."
            await interaction.followup.send(f"{prefix}\n{message}", ephemeral=True)

    @client.tree.command(
        name="princessrole",
        description="Set or view which role is treated as the Princess role",
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(role="Leave empty to show current setting")
    async def princessrole(
        interaction: discord.Interaction,
        role: discord.Role | None = None,
    ):
        if role is None:
            role_id = core.get_princess_role_id()
            if role_id is None:
                await interaction.response.send_message(
                    "Princess role is not configured.",
                    ephemeral=True,
                )
                return

            role_obj = interaction.guild.get_role(role_id) if interaction.guild else None
            if role_obj is not None:
                await interaction.response.send_message(
                    f"Princess role is set to {role_obj.mention}.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    f"Princess role is set to <@&{role_id}>.",
                    ephemeral=True,
                )
            return

        core.set_princess_role(role.id)
        await interaction.response.send_message(
            f"Princess role set to {role.mention}.",
            ephemeral=True,
        )

    @client.tree.command(
        name="rankupdateschannel",
        description="Set or view where rank updates are posted",
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(channel="Leave empty to show current setting")
    async def rankupdateschannel(
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ):
        if channel is None:
            settings = core.get_rank_update_channel_settings()
            channel_id = settings.get("rank_update_channel_id")
            fallback_name = settings.get("rank_update_channel_name", "JordanBot")
            if isinstance(channel_id, int) and interaction.guild is not None:
                found = interaction.guild.get_channel(channel_id)
                if isinstance(found, discord.TextChannel):
                    await interaction.response.send_message(
                        f"Rank updates channel is set to {found.mention}.",
                        ephemeral=True,
                    )
                    return
            await interaction.response.send_message(
                f"Rank updates channel is using fallback name: **{fallback_name}**.",
                ephemeral=True,
            )
            return

        core.set_rank_update_channel(channel.id)
        await interaction.response.send_message(
            f"Rank updates will be posted in {channel.mention}.",
            ephemeral=True,
        )

    @client.tree.command(
        name="tributeschannel",
        description="Set or view where tribute logs are posted",
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(channel="Leave empty to show current setting")
    async def tributeschannel(
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ):
        if channel is None:
            settings = core.get_tributes_channel_settings()
            channel_id = settings.get("tributes_channel_id")
            fallback_name = settings.get("tributes_channel_name", "tributes")
            if isinstance(channel_id, int) and interaction.guild is not None:
                found = interaction.guild.get_channel(channel_id)
                if isinstance(found, discord.TextChannel):
                    await interaction.response.send_message(
                        f"Tributes channel is set to {found.mention}.",
                        ephemeral=True,
                    )
                    return
            await interaction.response.send_message(
                f"Tributes channel is using fallback name: **{fallback_name}**.",
                ephemeral=True,
            )
            return

        core.set_tributes_channel(channel.id)
        await interaction.response.send_message(
            f"Tributes will be posted in {channel.mention}.",
            ephemeral=True,
        )

    @client.tree.command(
        name="rankconfigshow", description="Show current rank tier config"
    )
    @core.require_any_role(lambda: list(set(admin_group_getter() + common_group_getter())))
    @app_commands.describe(private="Show response privately (admins only)")
    async def rankconfigshow(
        interaction: discord.Interaction,
        private: bool = False,
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Could not resolve member.", ephemeral=True)
            return

        admin_role_ids = admin_group_getter()
        has_admin_access = core.has_any_role_id(interaction.user, admin_role_ids)
        if not admin_role_ids and interaction.user.guild_permissions.administrator:
            has_admin_access = True

        lines = []
        for index, tier in enumerate(core.get_rank_tiers(), start=1):
            role_id = int(tier["role_id"])
            role = interaction.guild.get_role(role_id) if interaction.guild else None
            role_display = role.mention if role else f"<@&{role_id}>"
            lines.append(f"{index}. {role_display} - {float(tier['avg_weekly']):.2f}")

        # Common-role users always receive a private response.
        ephemeral = True if not has_admin_access else bool(private)
        await interaction.response.send_message(
            "Current rank tiers:\n" + ("\n".join(lines) if lines else "(none)"),
            ephemeral=ephemeral,
        )

    @client.tree.command(
        name="rankconfigset",
        description="Add/update a rank role and weekly-average threshold",
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(
        role="Discord role for this rank tier",
        avg_weekly="Minimum average weekly send",
    )
    async def rankconfigset(
        interaction: discord.Interaction,
        role: discord.Role,
        avg_weekly: app_commands.Range[float, 0.0, 1000000.0],
    ):
        core.upsert_rank_tier_by_id(role.id, float(avg_weekly))
        await interaction.response.send_message(
            f"Saved tier {role.mention} at avg weekly {float(avg_weekly):.2f}. Run /calccurrentlevels to apply to everyone.",
            ephemeral=True,
        )

    async def autocomplete_rank_roles(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return only roles that are in the rank config."""
        if not interaction.guild:
            return []

        tiers = core.get_rank_tiers()
        configured_role_ids = {int(tier["role_id"]) for tier in tiers}

        choices = []
        for role_id in configured_role_ids:
            role = interaction.guild.get_role(role_id)
            if role and current.lower() in role.name.lower():
                choices.append(app_commands.Choice(name=role.name, value=str(role_id)))

        return choices[:25]

    @client.tree.command(
        name="rankconfigremove", description="Remove a rank tier by role"
    )
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(role="Discord role to remove from rank tiers")
    @app_commands.autocomplete(role=autocomplete_rank_roles)
    async def rankconfigremove(interaction: discord.Interaction, role: str):
        role_id = int(role)
        if not core.remove_rank_tier_by_id(role_id):
            await interaction.response.send_message(
                "No matching rank tier found, or at least one rank tier must remain.",
                ephemeral=True,
            )
            return

        role_obj = interaction.guild.get_role(role_id) if interaction.guild else None
        role_mention = role_obj.mention if role_obj else f"<@&{role_id}>"
        await interaction.response.send_message(
            f"Removed tier {role_mention}. Run /calccurrentlevels to apply to everyone.",
            ephemeral=True,
        )

    @client.tree.command(name="accessroleshow", description="Show configured command access role groups")
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(group="Role group to inspect")
    @app_commands.choices(group=ACCESS_GROUP_CHOICES)
    async def accessroleshow(
        interaction: discord.Interaction,
        group: app_commands.Choice[str],
    ):
        role_ids = core.get_access_role_ids(group.value)
        await interaction.response.send_message(
            f"{_group_label(group.value)} roles: {_format_role_mentions(role_ids)}",
            ephemeral=True,
        )

    @client.tree.command(name="accessroleadd", description="Add a role to admin/common command access group")
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(group="Which role group", role="Role to add")
    @app_commands.choices(group=ACCESS_GROUP_CHOICES)
    async def accessroleadd(
        interaction: discord.Interaction,
        group: app_commands.Choice[str],
        role: discord.Role,
    ):
        core.add_access_role(group.value, role.id)
        role_ids = core.get_access_role_ids(group.value)
        await interaction.response.send_message(
            f"Added {role.mention} to {_group_label(group.value)} roles. Now: {_format_role_mentions(role_ids)}",
            ephemeral=True,
        )

    async def autocomplete_access_roles_to_remove(
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Return only roles that are in admin or common access groups."""
        if not interaction.guild:
            return []

        admin_ids = core.get_access_role_ids("admin")
        common_ids = core.get_access_role_ids("common")
        all_configured_ids = set(admin_ids) | set(common_ids)

        choices = []
        for role_id in all_configured_ids:
            role = interaction.guild.get_role(role_id)
            if role and current.lower() in role.name.lower():
                choices.append(app_commands.Choice(name=role.name, value=str(role_id)))

        return choices[:25]

    @client.tree.command(name="accessroleremove", description="Remove a role from admin/common command access group")
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(group="Which role group", role="Role to remove")
    @app_commands.choices(group=ACCESS_GROUP_CHOICES)
    @app_commands.autocomplete(role=autocomplete_access_roles_to_remove)
    async def accessroleremove(
        interaction: discord.Interaction,
        group: app_commands.Choice[str],
        role: str,
    ):
        role_id = int(role)
        core.remove_access_role(group.value, role_id)
        role_ids = core.get_access_role_ids(group.value)
        role_obj = interaction.guild.get_role(role_id) if interaction.guild else None
        role_mention = role_obj.mention if role_obj else f"<@&{role_id}>"
        await interaction.response.send_message(
            f"Removed {role_mention} from {_group_label(group.value)} roles. Now: {_format_role_mentions(role_ids)}",
            ephemeral=True,
        )

    return {
        "backupnow": backupnow,
        "princessrole": princessrole,
        "rankupdateschannel": rankupdateschannel,
        "tributeschannel": tributeschannel,
        "rankconfig": rankconfigshow,
        "rankconfigset": rankconfigset,
        "rankconfigremove": rankconfigremove,
        "accessroleshow": accessroleshow,
        "accessroleadd": accessroleadd,
        "accessroleremove": accessroleremove,
    }
