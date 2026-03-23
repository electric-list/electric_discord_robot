import random

import discord
from discord import app_commands

import bot_core as core
import styles


def register_game_commands(
    client,
    admin_group_getter,
    common_group_getter,
):
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

    @client.tree.command(name="telljoke", description="Get a random joke")
    @core.require_any_role(admin_group_getter)
    async def telljoke(interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(styles.get().jokes))

    @client.tree.command(name="dice", description="Roll true dice and return an animated GIF")
    @core.require_any_role(common_group_getter)
    @app_commands.describe(
        dice_count="Number of dice to roll",
        dice_sides="Sides per die",
        multiplier="Multiply the dice sum by this",
        additive_modifier="Add/subtract this from the dice sum after multiplier",
        princess="Which princess this send is for",
    )
    @app_commands.choices(
        dice_sides=[
            app_commands.Choice(name="d4", value=4),
            app_commands.Choice(name="d6", value=6),
            app_commands.Choice(name="d8", value=8),
            app_commands.Choice(name="d10", value=10),
            app_commands.Choice(name="d12", value=12),
            app_commands.Choice(name="d20", value=20),
            app_commands.Choice(name="d100", value=100),
        ]
    )
    @app_commands.autocomplete(princess=autocomplete_princess_members)
    async def dice(
        interaction: discord.Interaction,
        dice_count: app_commands.Range[int, 1, 15],
        dice_sides: app_commands.Choice[int],
        princess: str,
        multiplier: app_commands.Range[float, 0.01, 1000.0] = 1.0,
        additive_modifier: app_commands.Range[float, -1000000.0, 1000000.0] = 0.0,
    ):
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

        sides = int(dice_sides.value)
        final_rolls = [random.randint(1, sides) for _ in range(int(dice_count))]
        base_sum = sum(final_rolls)
        modified_sum = base_sum * float(multiplier)
        total = round(modified_sum + float(additive_modifier), 2)
        gif_buffer = core.build_dice_roll_gif(
            int(dice_count),
            sides,
            final_rolls,
            float(additive_modifier),
            float(multiplier),
            interaction.user.display_name,
        )
        file = discord.File(gif_buffer, filename="dice-roll.gif")
        view = core.RecordSendFromGameView(
            interaction.user.id,
            float(total),
            "dice",
            princess_user_id=princess_member.id,
            princess_display_name=princess_member.display_name,
        )

        await interaction.response.defer(thinking=True)
        sent_message = await interaction.followup.send(
            content=styles.get().tpl_dice_result.format(
                mention=interaction.user.mention,
                formula=f"{dice_count}d{sides} x {float(multiplier):g} {float(additive_modifier):+g}",
                base_sum=base_sum,
                total=total,
            ),
            file=file,
            view=view,
            wait=True,
        )
        core.add_pending_game_view(
            sent_message.id,
            interaction.user.id,
            float(total),
            "dice",
            princess_user_id=princess_member.id,
            princess_display_name=princess_member.display_name,
        )

    @client.tree.command(name="wheelspin", description="Spin a number wheel and return an animated GIF")
    @core.require_any_role(common_group_getter)
    @app_commands.describe(
        minimum="Lowest number",
        maximum="Highest number",
        princess="Which princess this send is for",
    )
    @app_commands.autocomplete(princess=autocomplete_princess_members)
    async def wheelspin(
        interaction: discord.Interaction,
        minimum: app_commands.Range[int, 0, 10000],
        maximum: app_commands.Range[int, 0, 10000],
        princess: str,
    ):
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

        if maximum <= minimum:
            await interaction.response.send_message(
                "`maximum` must be greater than `minimum`.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)
        result = random.randint(minimum, maximum)
        gif_buffer = core.build_wheelspin_gif(
            minimum, maximum, result, interaction.user.display_name
        )
        file = discord.File(gif_buffer, filename="wheelspin.gif")
        view = core.RecordSendFromGameView(
            interaction.user.id,
            float(result),
            "wheelspin",
            princess_user_id=princess_member.id,
            princess_display_name=princess_member.display_name,
        )

        sent_message = await interaction.followup.send(
            content=styles.get().tpl_wheel_result.format(
                mention=interaction.user.mention,
                result=result,
            ),
            file=file,
            view=view,
            wait=True,
        )
        core.add_pending_game_view(
            sent_message.id,
            interaction.user.id,
            float(result),
            "wheelspin",
            princess_user_id=princess_member.id,
            princess_display_name=princess_member.display_name,
        )

    return {
        "telljoke": telljoke,
        "dice": dice,
        "wheelspin": wheelspin,
    }
