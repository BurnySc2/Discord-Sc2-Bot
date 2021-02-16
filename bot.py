import arrow

# https://discordpy.readthedocs.io/en/latest/api.html
import discord  # pip install discord
from discord.ext import commands

# https://discord-py-slash-command.readthedocs.io/en/latest/gettingstarted.html
from discord_slash import SlashCommand
from discord_slash.utils import manage_commands
import json, os
from typing import List, Dict, Set, Optional, Union
import asyncio
import sys

import traceback

from loguru import logger

from commands.public_mmr import public_mmr
from commands.public_remind import Remind

# from commands.public_vod import Vod

# Remove previous default handlers
logger.remove()
# Log to console
logger.add(sys.stdout, level="INFO")
# Log to file, max size 1 mb
logger.add("bot.log", rotation="1 MB", retention="1 month", level="INFO")


def write_error(error: Exception, file_name="bot_error.log"):
    path = os.path.dirname(__file__)
    log_path = os.path.join(path, file_name)

    time_now = arrow.now()
    time_now_readable = time_now.format()
    trace = traceback.format_exc()
    with open(log_path, "a") as f:
        f.write("\n")
        f.write(time_now_readable)
        f.write("\n")
        f.write(str(error))
        f.write("\n")
        f.write(trace)
    print(time_now_readable)
    print(trace, flush=True)


# Instanciate classes
client = commands.Bot(command_prefix="!")
slash = SlashCommand(client, sync_commands=True)
my_reminder: Remind = Remind(client)

# Static variables
guild_ids = [384968030423351298]
bot_folder_path = os.path.dirname(__file__)

# Load twitch client_id
client_id_path = os.path.join(bot_folder_path, "my_client_id.json")
client_id = ""
if os.path.exists(client_id_path):
    with open(client_id_path) as f:
        data: dict = json.load(f)
        client_id = data["client_id"]

# Load settings
settings_path = os.path.join(bot_folder_path, "settings.json")
settings = {}
if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings: dict = json.load(f)


bot_is_ready = False


@client.event
async def on_ready():
    global bot_is_ready
    await my_reminder.load_reminders()
    bot_is_ready = True
    print("Ready!")


@slash.slash(
    name="mmr",
    guild_ids=guild_ids,
    description="Grab the MMR of a specific player",
    options=[
        manage_commands.create_option(
            name="name",
            description="Name of the StarCraft 2 player you want to get MMR info of",
            # Option type: https://discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
            option_type=3,
            required=True,
        )
    ],
)
@client.command()
async def mmr(ctx: commands.Context, name: str):
    author: discord.User = ctx.author
    result = await public_mmr(author, name)
    channel: discord.TextChannel = ctx.channel
    await channel.send(f"@{author.name}\n{result}")


# TODO Re-enable command:
# async def vod(ctx: commands.Context, name: str):
#     # ctx.author
#     # ctx.channel
#     # ctx.command
#     # ctx.me
#     pass


@slash.slash(
    name="reminder",
    guild_ids=guild_ids,
    description="Remind yourself in the future",
    options=[
        manage_commands.create_option(
            name="time",
            description="When do you want to be reminded, e.g. '5h' reminds you in 5 hours.",
            # Option type: https://discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
            option_type=3,
            required=True,
        ),
        manage_commands.create_option(
            name="message",
            description="The message the bot will remind you of",
            # Option type: https://discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
            option_type=3,
            required=True,
        ),
    ],
)
@client.command()
async def reminder(ctx: commands.Context, time: str, message: str):
    author: discord.User = ctx.author
    channel: discord.TextChannel = ctx.channel
    response = await my_reminder.public_remind_in(ctx.message, author, channel, time, message)
    if isinstance(response, discord.Embed):
        await channel.send(f"@{author.name}", embed=response)
    elif response:
        await channel.send(f"@{author.name} {response}")


@slash.slash(
    name="remindat",
    guild_ids=guild_ids,
    description="Remind yourself in the future",
    options=[
        manage_commands.create_option(
            name="time",
            description="When do you want to be reminded, e.g. '14:30' reminds you in at 14:30.",
            # Option type: https://discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
            option_type=3,
            required=True,
        ),
        manage_commands.create_option(
            name="message",
            description="The message the bot will remind you of",
            # Option type: https://discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
            option_type=3,
            required=True,
        ),
    ],
)
@client.command()
async def remindat(ctx: commands.Context, time: str, message: str):
    author: discord.User = ctx.author
    channel: discord.TextChannel = ctx.channel
    response = await my_reminder.public_remind_at(ctx.message, author, channel, time, message)
    if isinstance(response, discord.Embed):
        await channel.send(f"@{author.name}", embed=response)
    elif response:
        await channel.send(f"@{author.name} {response}")


@client.command()
async def reminders(ctx: commands.Context, *args):
    author: discord.User = ctx.author
    channel: discord.TextChannel = ctx.channel
    response = await my_reminder.public_list_reminders(author, channel)
    if isinstance(response, discord.Embed):
        await channel.send(embed=response)
    elif response:
        await channel.send(f"@{author.name} {response}")


@slash.slash(
    name="delreminder",
    guild_ids=guild_ids,
    description="Remove a reminder",
    options=[
        manage_commands.create_option(
            name="reminder_id",
            description="Which reminder you want to remove. See !reminders",
            # Option type: https://discord.com/developers/docs/interactions/slash-commands#applicationcommandoptiontype
            option_type=3,
            required=True,
        ),
    ],
)
@client.command()
async def delreminder(ctx: commands.Context, reminder_id: str):
    author: discord.User = ctx.author
    response = await my_reminder.public_del_remind(author, reminder_id)
    channel: discord.TextChannel = ctx.channel
    if isinstance(response, discord.Embed):
        await channel.send(f"@{author.name}", embed=response)
    elif response:
        await channel.send(f"@{author.name} {response}")


async def loop_function():
    """ A function that is called every X seconds based on the asyncio.sleep(time) below. """
    global bot_is_ready
    while 1:
        await asyncio.sleep(1)
        # Wait until bot is ready until it gets called
        # TODO If bot disconnects, un-ready the bot?
        if bot_is_ready:
            await my_reminder.tick()


if __name__ == "__main__":
    path = os.path.dirname(__file__)
    # Load bot key
    with open(os.path.join(path, "my_key.json")) as file:
        key = json.load(file)["key"]
    try:
        client.loop.create_task(loop_function())
        client.run(key)
    except Exception as e:
        write_error(e)

# TODO Enable/use the following functions:
# async def on_connect(self):
#     """ Called after reconnect? """
#     print("Connected on as {0}!".format(self.user))
#
# async def on_resumed(self):
#     """ Called after reconnect / resume? """
#     print("Resumed on as {0}!".format(self.user))
#
# async def on_disconnect(self):
#     """ Called after disconnect """
#     print("Disconnected!")
#
# async def on_ready(self):
#     await self.load_settings()
#     await self.reminder.load_reminders()

#
# async def save_settings(self):
#     """ Save settings to disk after every change """
#     if hasattr(self, "settings"):
#         settings_path = os.path.join(self.bot_folder_path, "settings.json")
#         with open(settings_path, "w") as f:
#             json.dump(self.settings, f, indent=2)

#
# async def list_public_commands(self):
#     # TODO Add a helper command to display which commands are all available
#     pass
