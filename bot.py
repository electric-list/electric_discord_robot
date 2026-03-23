import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import bot_core as core
import styles
from bot_commands.config_commands import register_config_commands
from bot_commands.game_commands import register_game_commands
from bot_commands.progression_commands import register_progression_commands
from bot_commands.request_commands import register_request_commands
from errorhandling import register_error_handlers

# Load style before command registration so jokes and templates are available at startup.
styles.load_from_config()

# TODO
# look if we can generate very nice messages
# role names: Baby Simp, Tiny Tribute, Allowance Apprentice, Wallet Warming, Good Little Sub, Princess Supporter, Loyal Sender, Tribute Regular, Premium Simp, Elite Devotee, Royal Provider, Princess Favorite, Crowned Contributor, Treasury Knight, Ultimate Wallet

# --- initialize bot ---
load_dotenv()
intents = discord.Intents.default()
intents.message_content = True


class JordansBot(commands.Bot):
    async def setup_hook(self):
        # Reload style and settings/ranks, then register persistent views.
        styles.load_from_config()
        core.initialize_runtime_state()
        core.restore_persistent_views(self)


client = JordansBot(command_prefix="!", intents=intents)

# --- load config ---
token = os.getenv("TOKEN")
guild_id_raw = os.getenv("GUILD_ID")
commands_synced = False

# --- command registration ---
all_commands = {}
admin_group_getter = lambda: core.get_access_role_ids("admin")
common_group_getter = lambda: core.get_access_role_ids("common")
all_commands.update(register_config_commands(client, admin_group_getter, common_group_getter))
all_commands.update(register_progression_commands(client, admin_group_getter, common_group_getter))
all_commands.update(register_game_commands(client, admin_group_getter, common_group_getter))
all_commands.update(register_request_commands(client, admin_group_getter, common_group_getter))
register_error_handlers(all_commands, core.send_interaction_error)


# --- bot events ---
@client.event
async def on_ready():
    global commands_synced

    if not commands_synced:
        if guild_id_raw:
            try:
                guild_id = int(guild_id_raw)
                guild_obj = discord.Object(id=guild_id)
                client.tree.copy_global_to(guild=guild_obj)
                client.tree.clear_commands(guild=None)
                await client.tree.sync()
                synced = await client.tree.sync(guild=guild_obj)
                print(f"Synced {len(synced)} guild slash command(s) to guild {guild_id}.")
            except ValueError:
                print("GUILD_ID is set but is not a valid integer. Falling back to global sync.")
                synced = await client.tree.sync()
                print(f"Synced {len(synced)} global slash command(s).")
        else:
            synced = await client.tree.sync()
            print(
                f"Synced {len(synced)} global slash command(s). "
                "Global commands can take time to show up."
            )

        print("Tip: set GUILD_ID in your .env for near-instant slash command updates in a test server.")
        commands_synced = True

    print(f"Logged in as a bot {client.user}")


@client.event
async def on_message(message: discord.Message):
    _ = message
    # External message scanning is intentionally disabled.
    # Future integrations should call core.process_external_send_event(...).
    return


# --- run bot ---
if not token:
    raise RuntimeError("TOKEN is not set. Add it to your .env file or environment.")

client.run(token)
