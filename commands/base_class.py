# https://discordpy.readthedocs.io/en/latest/api.html
import discord
import json, os, re
from typing import List, Dict, Set, Optional, Union
import asyncio

# http://zetcode.com/python/prettytable/
from prettytable import PrettyTable  # pip install PTable
import traceback


class BaseClass(discord.Client):
    def __init__(self):
        super().__init__()
        self.owner = "BuRny#8752"
        self.client_id = ""
        self.trigger = "!"
        self.settings = {}

    async def _get_message_as_list(self, message: discord.Message) -> List[str]:
        """ Parse a message and return the message as list (without the trigger at the start) """
        trigger: str = await self._get_setting_server_value(message.guild, "trigger")
        # trigger = self.settings["servers"][str(message.guild.id)]["trigger"]
        message_content: str = message.content
        message_without_trigger: str = message_content[len(trigger) :]
        message_as_list = message_without_trigger.split(" ")
        return message_as_list
