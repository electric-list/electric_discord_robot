import discord
from discord import app_commands

import bot_core as core
import styles


def register_request_commands(client, admin_group_getter, common_group_getter):
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

    @client.tree.command(name="requestsend", description="Princess requests a send amount")
    @core.require_any_role(admin_group_getter)
    @app_commands.describe(
        amount="Requested amount",
        member="Optional member to request from",
        reimbursement_item="Optional item being reimbursed",
        note="Optional short note",
    )
    async def requestsend(
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.01, 1000000.0],
        member: discord.Member | None = None,
        reimbursement_item: str | None = None,
        note: str | None = None,
    ):
        target_text = f" from {member.mention}" if member else ""
        reimbursement_item_value = reimbursement_item.strip() if reimbursement_item else None
        note_text = f"\nNote: {note}" if note else ""
        view = core.RequestView(
            interaction.user.mention,
            amount,
            target_text,
            note,
            reimbursement_item_value,
            member.id if member else None,
            interaction.user.id if isinstance(interaction.user, discord.Member) else None,
            interaction.user.display_name if isinstance(interaction.user, discord.Member) else None,
        )

        if reimbursement_item_value:
            await interaction.response.send_message(
                styles.get().tpl_request_reimburse.format(
                    mention=interaction.user.mention,
                    amount=amount,
                    item=reimbursement_item_value,
                    target_text=target_text,
                    note_text=note_text,
                ),
                view=view,
            )
        else:
            await interaction.response.send_message(
                styles.get().tpl_request_send.format(
                    mention=interaction.user.mention,
                    amount=amount,
                    target_text=target_text,
                    note_text=note_text,
                ),
                view=view,
            )
        sent_message = await interaction.original_response()
        core.add_pending_request_view(
            sent_message.id,
            interaction.user.mention,
            amount,
            target_text,
            note,
            reimbursement_item_value,
            member.id if member else None,
            interaction.user.id if isinstance(interaction.user, discord.Member) else None,
            interaction.user.display_name if isinstance(interaction.user, discord.Member) else None,
        )

    @client.tree.command(
        name="iamasubandisent",
        description="Sub requests that a send is registered (Princess approval required)",
    )
    @core.require_any_role(common_group_getter)
    @app_commands.describe(
        amount="Amount you sent",
        platform="Where you sent it",
        princess="Which princess this send was for",
        note="Optional note",
    )
    @app_commands.autocomplete(princess=autocomplete_princess_members)
    async def iamasubandisent(
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.01, 1000000.0],
        platform: app_commands.Range[str, 1, 64],
        princess: str,
        note: str | None = None,
    ):
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Could not resolve member.", ephemeral=True
            )
            return

        platform_value = platform.strip()
        if not platform_value:
            await interaction.response.send_message(
                "Platform is required.", ephemeral=True
            )
            return

        try:
            princess_id = int(princess)
        except (TypeError, ValueError):
            await interaction.response.send_message(
                "Please select a valid princess.", ephemeral=True
            )
            return

        guild = interaction.guild
        princess_member = guild.get_member(princess_id) if guild is not None else None
        if princess_member is None and guild is not None:
            try:
                princess_member = await guild.fetch_member(princess_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                princess_member = None

        if princess_member is None or not core.is_princess_member(princess_member):
            await interaction.response.send_message(
                "Please select a valid princess.", ephemeral=True
            )
            return

        note_text = f"\nNote: {note}" if note else ""
        princess_context = f"\nFor: {princess_member.mention}"
        view = core.SubSendClaimView(
            interaction.user.id,
            float(amount),
            note,
            platform_value,
            princess_user_id=princess_member.id,
            princess_display_name=princess_member.display_name,
        )
        await interaction.response.send_message(
            styles.get().tpl_sub_sent.format(
                mention=interaction.user.mention,
                amount=float(amount),
                platform=platform_value,
                note_text=f"{princess_context}{note_text}",
            ),
            view=view,
        )
        sent_message = await interaction.original_response()
        core.add_pending_sub_claim_view(
            sent_message.id,
            interaction.user.id,
            float(amount),
            note,
            platform_value,
            princess_user_id=princess_member.id,
            princess_display_name=princess_member.display_name,
        )

    return {
        "requestsend": requestsend,
        "iamasubandisent": iamasubandisent,
    }
