#!/usr/bin/python3.6

import arrow

# https://discordpy.readthedocs.io/en/latest/api.html
import discord  # pip install discord
import json, os, re
from typing import List, Dict, Set, Optional, Union
import asyncio

# http://zetcode.com/python/prettytable/
from prettytable import PrettyTable  # pip install PTable
import traceback

from loguru import logger

from commands.public_vod import Vod
from commands.public_mmr import Mmr
from commands.admin_add_role import Role
from commands.admin_add_admin import Admin
from commands.public_remind import Remind


def write_error(error: Exception, file_name="error_log.txt"):
    path = os.path.dirname(__file__)
    log_path = os.path.join(path, file_name)

    time_now = arrow.now()
    time_now_readable = time_now.format()
    trace = traceback.format_exc()
    with open(log_path, "a") as f:
        f.write(time_now_readable)
        f.write(str(error))
        f.write(trace)
    print(time_now_readable)
    print(trace, flush=True)


class Bot(Admin, Role, Mmr, Vod, discord.Client):
    def __init__(self):
        super().__init__()
        self.debug_mode = False

        self.bot_folder_path = os.path.dirname(__file__)
        self.client_id = None

        self.reminder: Remind = Remind(self)

        if self.debug_mode:
            logger.warning(f"Bot started in debug mode! It will ignore all channels except bot_tests channel.")

        self.admin_commands = {
            "addrole": self.admin_add_role,
            "delrole": self.admin_del_role,
            "addadmin": self.admin_add_admin,
            "deladmin": self.admin_del_admin,
            "vodaddchannel": self.admin_add_vod_channel,
            "voddelchannel": self.admin_del_vod_channel,
        }
        self.public_commands = {
            "commands": self.list_public_commands,
            "mmr": self.public_mmr,
            "vod": self.public_vod,
            "reminder": self.reminder.public_remind_in,
            "remindat": self.reminder.public_remind_at,
            "reminders": self.reminder.public_list_reminders,
            "delreminder": self.reminder.public_del_remind,
        }

        self.loop.create_task(self.loop_function())

    async def loop_function(self):
        """ A function that is called every X seconds based on the asyncio.sleep(time) below. """
        while 1:
            await asyncio.sleep(1)
            await self.reminder.tick()

    async def on_connect(self):
        """ Called after reconnect? """
        print("Connected on as {0}!".format(self.user))

    async def on_resumed(self):
        """ Called after reconnect / resume? """
        print("Resumed on as {0}!".format(self.user))

    async def on_disconnect(self):
        """ Called after disconnect """
        print("Disconnected!")

    async def on_ready(self):
        await self.initialize()
        await self.load_settings()
        await self.reminder.load_reminders()

    async def initialize(self):
        """ Set default parameters when bot is started """
        print("Initialized", flush=True)

    async def load_settings(self):
        """ Load settings from local settings.json file after bot is started """
        settings_path = os.path.join(self.bot_folder_path, "settings.json")
        if os.path.exists(settings_path):
            try:
                with open(settings_path) as f:
                    data: dict = json.load(f)
                    self.settings.update(data)
            except json.decoder.JSONDecodeError:
                borken_path = os.path.join(self.bot_folder_path, "settings_borken.json")
                if os.path.exists(borken_path):
                    os.remove(settings_path)
                else:
                    os.rename(settings_path, borken_path)

        # Load twitch client_id
        client_id_path = os.path.join(self.bot_folder_path, "my_client_id.json")
        if os.path.exists(client_id_path):
            with open(client_id_path) as f:
                data: dict = json.load(f)
                self.client_id = data["client_id"]

        self.loaded_settings = True

    async def save_settings(self):
        """ Save settings to disk after every change """
        if hasattr(self, "settings"):
            settings_path = os.path.join(self.bot_folder_path, "settings.json")
            with open(settings_path, "w") as f:
                json.dump(self.settings, f, indent=2)

    async def on_message(self, message: discord.Message):
        """ When a message was sent, parse message and act if it was a command """
        if message.author.bot:
            # Message was by bot (itself)
            return

        while not hasattr(self, "loaded_settings"):
            # Settings have not been loaded yet
            await asyncio.sleep(1)

        if message.guild is None:
            # Message was sent privately
            pass
        else:
            # if message.channel.name != "bot_tests":
            #     print(f"Ignoring message in channel `{message.channel.name}`")
            #     return

            # Message was sent in a server
            if not self.debug_mode or message.channel.name == "bot_tests":
                print(f"Received message in channel {message.channel}: {message.content}", flush=True)
                try:
                    await self._handle_server_message(message)
                except Exception as e:
                    write_error(e)

    async def _handle_server_message(self, message: discord.Message):
        await self._add_server_to_settings(message)

        if str(message.guild.id) in self.settings["servers"]:
            trigger: str = await self._get_setting_server_value(message.guild, "trigger")
            server_admins: List[str] = await self._get_setting_server_value(message.guild, "admins", list)
            allowed_roles: Set[discord.Role] = {
                role for role in (await self._get_setting_server_value(message.guild, "allowed_roles", list))
            }
            # Check if message author has right to use certain commands
            author_in_allowed_roles = any(role.name in allowed_roles for role in message.author.roles)
            author_in_admins = str(message.author) in server_admins

            if message.content.startswith(trigger):
                message_content: str = message.content
                message_without_trigger: str = message_content[len(trigger) :]
                message_as_list = message_without_trigger.split(" ")
                command_name = message_as_list[0].strip().lower()

                if command_name in self.public_commands and (author_in_allowed_roles or author_in_admins):
                    function = self.public_commands[command_name]
                    await function(message)
                    return
                elif command_name in self.public_commands and not author_in_allowed_roles and not author_in_admins:
                    # User not allowed to use this command
                    print(f"User {str(message.author)} not allowed to use command {command_name}", flush=True)
                    return

                if command_name in self.admin_commands and author_in_admins:
                    function = self.admin_commands[command_name]
                    await function(message)
                    return
                elif command_name in self.admin_commands and not author_in_admins:
                    # User not allowed to use this command
                    return

                if command_name not in self.admin_commands and command_name not in self.public_commands:
                    # await self.send_message(message.channel, f"{message.author.mention} command \"{command_name}\" not found.")
                    print(f'{message.author.mention} command "{command_name}" not found.', flush=True)

    async def _get_setting_server_value(self, server, variable_name: str, variable_type: type = str):
        changed = False
        if "servers" not in self.settings:
            self.settings["servers"] = {}
            changed = True

        if str(server.id) not in self.settings["servers"]:
            self.settings["servers"][str(server.id)] = {}
            changed = True

        if variable_name not in self.settings["servers"][str(server.id)]:
            self.settings["servers"][str(server.id)][variable_name] = variable_type()
            changed = True

        if changed:
            await self.save_settings()

        assert (
            type(self.settings["servers"][str(server.id)][variable_name]) == variable_type
        ), f"{variable_name} not of type {variable_type}"
        return self.settings["servers"][str(server.id)][variable_name]

    async def _add_server_to_settings(self, message: discord.Message):
        """ First message was sent in a specific server, initialize dictionary/settings """
        if self.settings.get("servers", None) is None:
            self.settings["servers"] = {}
        if str(message.guild.id) not in self.settings["servers"]:
            print(
                f"Server {message.guild.name} not in settings, adding {message.guild.id} to self.settings", flush=True
            )
            self.settings["servers"][str(message.guild.id)] = {
                # The command trigger that the bot listens to
                "trigger": "!",
                # The owner of the server
                "owner": str(message.guild.owner),
                # Admins that have special command rights, by default bot owner and discord server owner
                "admins": list({self.owner, str(message.guild.owner)}),
                # Roles that are allowed to use the public commands
                # "allowed_roles": [],
                # When "vod" command is used, it will respond in the same channel and also in the dedicated channels below
                # "vod_channels": [],
            }
            await self.save_settings()

    async def list_public_commands(self):
        # TODO
        pass


if __name__ == "__main__":
    path = os.path.dirname(__file__)
    with open(os.path.join(path, "my_key.json")) as file:
        key = json.load(file)["key"]
    bot = Bot()
    try:
        bot.run(key)
    except Exception as e:
        write_error(e)
