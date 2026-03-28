from discord import app_commands


class IgnoredGuildInteraction(app_commands.CheckFailure):
    pass


def bind_command_error_handler(command, command_name: str, send_interaction_error):
    @command.error
    async def _handler(interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await send_interaction_error(interaction, str(error))
            return
        await send_interaction_error(
            interaction, f"Something went wrong while running `/{command_name}`."
        )


def register_error_handlers(command_map: dict, send_interaction_error):
    for command_name, command in command_map.items():
        bind_command_error_handler(command, command_name, send_interaction_error)


def register_tree_error_handler(client, send_interaction_error):
    @client.tree.error
    async def _on_tree_error(interaction, error: app_commands.AppCommandError):
        # When the same bot token is running in multiple processes, one process can
        # receive an interaction for a guild-specific command that only the other
        # process has synced locally. Ignore that cross-instance noise.
        if isinstance(error, (app_commands.CommandNotFound, IgnoredGuildInteraction)):
            return

        if isinstance(error, app_commands.CheckFailure):
            await send_interaction_error(interaction, str(error))
            return

        await send_interaction_error(
            interaction,
            "Something went wrong while handling that slash command.",
        )


def register_tree_guild_filter(client, allowed_guild_id: int | None):
    async def _guild_filter(interaction) -> bool:
        if allowed_guild_id is None:
            return True
        if interaction.guild_id == allowed_guild_id:
            return True
        raise IgnoredGuildInteraction()

    client.tree.interaction_check = _guild_filter
