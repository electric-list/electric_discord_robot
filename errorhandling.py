from discord import app_commands


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
