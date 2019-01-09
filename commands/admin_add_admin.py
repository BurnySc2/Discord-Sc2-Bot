# https://pendulum.eustace.io/docs/
import pendulum
# https://discordpy.readthedocs.io/en/latest/api.html
import discord
import json, os, re
from typing import List, Dict, Set, Optional, Union
import asyncio
from aiohttp_requests import requests
# http://zetcode.com/python/prettytable/
from prettytable import PrettyTable # pip install PTable
import traceback

from .base_class import BaseClass

class Admin(BaseClass):
    async def _get_member_match(self, message: discord.Message, member_name: str) -> List[discord.Member]:
        """ Return all matches that match a specific user name substring """
        matches = [member for member in message.server.members if member_name.lower() in str(member).lower()]
        return matches


    async def admin_add_admin(self, message: discord.Message):
        await self._handle_admins(message, remove_admin=False)


    async def admin_del_admin(self, message: discord.Message):
        await self._handle_admins(message, remove_admin=True)


    async def _handle_admins(self, message: discord.Message, remove_admin=False):
        """ Similar to roles, this function adds/removes a user (name#tag) to the admin list """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]
        admins = await self._get_setting_server_value(message.server, "admins", list)
        print("admins:", admins)
        admins_changed = False
        response = []

        def handle_matches(matches):
            nonlocal admins, response, admins_changed, remove_admin, username
            print("matches", matches)
            if len(matches) > 1:
                matches_str = ", ".join(str(match) for match in matches)
                response.append(f"Found multiple users with name `{username}`: `{matches_str}`")
            elif len(matches) == 1:
                match = matches[0]
                match_name = str(match)
                print(match_name, admins)
                exists = match_name in admins
                print(exists)

                if not remove_admin and exists:
                    # Wanted to add name, but role is already in list
                    response.append(f"Found match for name `{username}`: `{match_name}` but name was already in admin list")
                elif not remove_admin and not exists:
                    # Add name as it is not in the list yet
                    admins_changed = True
                    admins.append(match_name)
                    response.append(f"Found match for name `{username}`: Added `{match_name}` to bot admin list")
                elif remove_admin and not exists:
                    # Wanted to remove name but is not in list
                    response.append(f"Found match for name `{username}`: `{match_name}` but name was not in bot admin list")
                elif remove_admin and exists:
                    # Wanted to remove user from list
                    admins_changed = True
                    admins.remove(match_name)
                    response.append(f"Found match for name `{username}`: Removed `{match_name}` from bot admin list")

            else:
                response.append(f"No match found for name `{username}`")
            return

        if not content_as_list:
            # Incorrect command usage
            if not remove_admin:
                response_complete = f"{message.author.mention} correct usage:\n{trigger}addadmin name\nor\n{trigger}addadmin name1 name2 name3"
            else:
                response_complete = f"{message.author.mention} correct usage:\n{trigger}deladmin name\nor\n{trigger}deladmin name1 name2 name3"

        else:
            # Correct usage
            for username in content_as_list:
                matches: List[discord.Member] = await self._get_member_match(message, username)
                handle_matches(matches)
            joined_responses = "\n".join(response)
            response_complete = f"{message.author.mention}\n{joined_responses}"
            if admins_changed:
                await self.save_settings()
        await self.send_message(message.channel, response_complete)
