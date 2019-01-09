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

class Role(BaseClass):
    async def _get_role_match(self, message: discord.Message, role_name: str):
        """ Finds all roles in the server that match a specific substring """
        matches: List[discord.Role] = [role for role in message.server.roles if role_name.lower() in role.name.lower()]
        return matches


    async def admin_add_role(self, message: discord.Message):
        await self._admin_handle_roles(message, remove_roles=False)


    async def admin_del_role(self, message: discord.Message):
        await self._admin_handle_roles(message, remove_roles=True)


    async def _admin_handle_roles(self, message: discord.Message, remove_roles=False):
        """ Add/remove server roles to settings that are allowed to use the public commands """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]

        allowed_roles = await self._get_setting_server_value(message.server, "allowed_roles", list)

        response = []
        roles_changed = False

        def handle_matches(matches):
            nonlocal allowed_roles, response, roles_changed, remove_roles
            if len(matches) > 1:
                matches_str = ", ".join(match.name for match in matches)
                response.append(f"Found multiple matches for role `{role_name}`: `{matches_str}`")
            elif len(matches) == 1:
                exists = matches[0].name in allowed_roles
                if not remove_roles and exists:
                    # Wanted to add role, but role is already in list
                    response.append(f"Found match for role `{role_name}`: `{matches[0]}`, but it was already listed in allowed roles")
                elif not remove_roles and not exists:
                    # Add role as it is not in the list yet
                    roles_changed = True
                    allowed_roles.append(matches[0].name)
                    response.append(f"Found match for role `{role_name}`: Added `{matches[0]}` to allowed roles")
                elif remove_roles and not exists:
                    # Wanted to remove role but is not in list
                    response.append(f"Found match for role `{role_name}`: `{matches[0]}`, but it was not listed in allowed roles")
                elif remove_roles and exists:
                    # Wanted to remove role but is not in list
                    roles_changed = True
                    allowed_roles.remove(matches[0].name)
                    response.append(f"Found match for role `{role_name}`: Removed `{matches[0]}` from allowed roles")
            else:
                response.append(f"No match found for role `{role_name}`")
            return

        if not content_as_list:
            # Incorrect command usage
            if not remove_roles:
                response_complete = f"{message.author.mention} correct usage:\n{trigger}addrole role\nor\n{trigger}addrole role1 role2 role3"
            else:
                response_complete = f"{message.author.mention} correct usage:\n{trigger}delrole role\nor\n{trigger}addrole role1 role2 role3"
        else:
            # Correct usage
            for role_name in content_as_list:
                matches = await self._get_role_match(message, role_name)
                handle_matches(matches)
            joined_responses = "\n".join(response)
            response_complete = f"{message.author.mention}\n{joined_responses}"
            if roles_changed:
                await self.save_settings()

        await self.send_message(message.channel, response_complete)
