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


class Bot(discord.Client):
    async def on_ready(self):
        await self.initialize()
        await self.load_settings()

    async def initialize(self):
        """ Set default parameters when bot is started """
        self.owner = "BuRny#8752"
        self.client_id = ""
        self.trigger = "!"
        self.settings = {}
        self.bot_folder_path = os.path.dirname(__file__)
        self.admin_commands = {
            "addrole": self.admin_add_role,
            "delrole": self.admin_del_role,
            "addadmin": self.admin_add_admin,
            "deladmin": self.admin_del_admin,
        }
        self.public_commands = {
            "commands": self.list_public_commands,
            "mmr": self.public_mmr,
            "vod": self.public_vod,
        }
        print("Initialized")

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
                json.dump(self.settings, f)

    async def on_message(self, message: discord.Message):
        """ When a message was sent, parse message and act if it was a command """
        if message.author.bot:
            # Message was by bot
            return

        while not hasattr(self, "loaded_settings"):
            # Settings have not been loaded yet
            await asyncio.sleep(1)

        if message.server is None:
            # Message was sent privately
            pass
        else:
            # Message was sent in a server
            print(f"Received message in channel {message.channel}: {message.content}")
            await self._add_server_to_settings(message)

            if message.server.id in self.settings["servers"]:
                trigger = self.settings["servers"][message.server.id]["trigger"]
                server_admins = self.settings["servers"][message.server.id]["admins"]
                allowed_roles: Set[discord.Role] = {role for role in self.settings["servers"][message.server.id]["allowed_roles"]}
                # Check if message author has right to use certain commands
                author_in_allowed_roles = any(role.name in allowed_roles for role in message.author.roles)
                author_in_admins = str(message.author) in server_admins
                # print(f"{message.author}: In allowed roles: {author_in_allowed_roles}, is admin: {author_in_admins}, author roles: {[role.name for role in message.author.roles]}, server roles: {allowed_roles}")

                if message.content.startswith(trigger):
                    message_content: str = message.content
                    message_without_trigger: str = message_content[len(trigger):]
                    message_as_list = message_without_trigger.split(" ")
                    command_name = message_as_list[0].strip().lower()

                    if command_name in self.public_commands and (author_in_allowed_roles or author_in_admins):
                        function = self.public_commands[command_name]
                        await function(message)
                        return
                    elif command_name in self.public_commands and not author_in_allowed_roles and not author_in_admins:
                        # User not allowed to use this command
                        print(f"User {str(message.author)} not allowed to use command {command_name}")
                        return

                    if command_name in self.admin_commands and author_in_admins:
                        function = self.admin_commands[command_name]
                        await function(message)
                        return
                    elif command_name in self.admin_commands and not author_in_admins:
                        # User not allowed to use this command
                        return

                    if command_name not in self.admin_commands and command_name not in self.public_commands:
                        await self.send_message(message.channel, f"{message.author.mention} command \"{command_name}\" not found.")
                        return
        # await self.send_message(message.channel, 'Hello World!')


    async def _add_server_to_settings(self, message: discord.Message):
        """ First message was sent in a specific server, initialize dictionary/settings """
        if self.settings.get("servers", None) is None:
            self.settings["servers"] = {}
        if message.server.id not in self.settings["servers"]:
            print(f"Server {message.server.name} not in settings, adding {message.server.id} to self.settings")
            self.settings["servers"][message.server.id] = {
                # The command trigger that the bot listens to
                "trigger": "!",
                # The owner of the server
                "owner": str(message.server.owner),
                # Admins that have special command rights, by default bot owner and discord server owner
                "admins": list({self.owner, str(message.server.owner)}),
                # Roles that are allowed to use the public commands
                "allowed_roles": [],
            }
            await self.save_settings()


    async def _get_message_as_list(self, message: discord.Message) -> List[str]:
        """ Parse a message and return the message as list (without the trigger at the start) """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        message_content: str = message.content
        message_without_trigger: str = message_content[len(trigger):]
        message_as_list = message_without_trigger.split(" ")
        return message_as_list


    async def _get_role_match(self, message: discord.Message, role_name: str):
        """ Finds all roles in the server that match a specific substring """
        matches: List[discord.Role] = [role for role in message.server.roles if role_name.lower() in role.name.lower()]
        return matches


    async def admin_add_role(self, message: discord.Message):
        """ Add server roles to settings that are allowed to use the public commands """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]
        allowed_roles = self.settings["servers"][message.server.id]["allowed_roles"]

        response = []
        roles_changed = False

        def handle_matches(matches):
            nonlocal allowed_roles, response, roles_changed
            if len(matches) > 1:
                matches_str = ", ".join(match.name for match in matches)
                response.append(f"Found multiple matches for role `{role_name}`: `{matches_str}`")
            elif len(matches) == 1:
                if matches[0].name in allowed_roles:
                    response.append(f"Found match for `{role_name}`: `{matches[0]}`, but it was already listed in allowed roles")
                else:
                    roles_changed = True
                    allowed_roles.append(matches[0].name)
                    response.append(f"Found role for `{role_name}`: Added `{matches[0]}` to allowed roles")
            else:
                response.append(f"No match found for role `{role_name}`")
            return

        if not content_as_list:
            # Incorrect command usage
            response_complete = f"{message.author.mention} correct usage:\n{trigger}addrole role\nor\n{trigger}addrole role1 role2 role3"
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


    async def admin_del_role(self, message: discord.Message):
        """ Same as above but reverted - Remove roles that match the command arguments """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]
        allowed_roles = set(self.settings["servers"][message.server.id]["allowed_roles"])

        response = []
        roles_changed = False

        def handle_matches(matches):
            nonlocal allowed_roles, response, roles_changed
            if len(matches) > 1:
                matches_str = ", ".join(match.name for match in matches)
                response.append(f"Found multiple matches for role `{role_name}`: `{matches_str}`")
            elif len(matches) == 1:
                if matches[0].name not in allowed_roles:
                    response.append(f"Found role for {role_name}: `{matches[0]}`, but it isn't listed in allowed roles")
                else:
                    roles_changed = True
                    allowed_roles.remove(matches[0].name)
                    response.append(f"Found role for {role_name}: Removed `{matches[0]}` from allowed roles")
            else:
                response.append(f"No match found for role `{role_name}`")
            return

        if not content_as_list:
            # Incorrect command usage
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


    async def _get_member_match(self, message: discord.Message, member_name: str) -> List[discord.Member]:
        """ Return all matches that match a specific user name substring """
        matches = [member for member in message.server.members if member_name.lower() in member.name.lower()]
        return matches


    async def admin_add_admin(self, message: discord.Message):
        """ Similar to roles, this function adds a user (name#tag) to the admin list """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]
        admins = self.settings["servers"][message.server.id]["admins"]

        admins_changed = False
        response = []

        def handle_matches(matches):
            nonlocal admins, response, admins_changed
            if len(matches) > 1:
                matches_str = ", ".join(str(match) for match in matches)
                response.append(f"Found multiple users with name `{username}`: `{matches_str}`")
            elif len(matches) == 1:
                match = matches[0]
                if str(match) in admins:
                    response.append(f"Found user for name `{username}`: `{str(match)}`, but username was already found in list of bot admins")
                else:
                    admins_changed = True
                    admins.append(match.name)
                    response.append(f"Found user for name `{username}`: Added `{str(match)}` to list of bot admins")
            else:
                response.append(f"No match found for name `{username}`")
            return

        if not content_as_list:
            # Incorrect command usage
            response_complete = f"{message.author.mention} correct usage:\n{trigger}addadmin name\nor\n{trigger}addadmin name1 name2 name3"
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


    async def admin_del_admin(self, message: discord.Message):
        """ Similar to roles, this function removes a user (name#tag) from the admin list """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]
        admins = self.settings["servers"][message.server.id]["admins"]

        admins_changed = False
        response = []

        def handle_matches(matches):
            nonlocal admins, response, admins_changed
            if len(matches) > 1:
                matches_str = ", ".join(str(match) for match in matches)
                response.append(f"Found multiple users with name `{username}`: `{matches_str}`")
            elif len(matches) == 1:
                match = matches[0]
                if str(match) not in admins:
                    response.append(f"Found user for name `{username}`: `{str(match)}`, but username was not found in list of bot admins")
                else:
                    admins_changed = True
                    admins.remove(match.name)
                    response.append(f"Found user for name `{username}`: Removed `{str(match)}` to list of bot admins")
            else:
                response.append(f"No match found for name `{username}`")
            return

        if not content_as_list:
            # Incorrect command usage
            response_complete = f"{message.author.mention} correct usage:\n{trigger}addadmin name\nor\n{trigger}addadmin name1 name2 name3"
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


    async def public_mmr(self, message: discord.Message):
        """ The public command '!mmr name', will look up an account name, clan name or stream name and list several results as a markdown table using PrettyTable
        Usage:
        !mmr twitch.tv/rotterdam08
        !mmr rotterdam
        !mmr [zelos] """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]
        response = []

        def format_result(api_entry):
            league_dict = {
                "grandmaster": "GM",
                "master": "M",
                "diamond": "D",
                "platinum": "P",
                "gold": "G",
                "silver": "S",
                "bronze": "B",
            }
            utc_timezone = pendulum.timezone("Etc/GMT0")
            utc_time_now = pendulum.now(utc_timezone)

            clan_tag: str = api_entry["clan_tag"]
            account_name: str = api_entry["acc_name"]
            display_name: str = api_entry["display_name"]
            full_display_name = (f"[{clan_tag}]" if clan_tag else "") + account_name + (f" ({display_name})" if display_name and display_name != account_name else "")
            wins: int = api_entry["wins"]
            losses: int = api_entry["losses"]
            stream_name: str = api_entry["stream_name"]

            def format_time_readable(time_difference: pendulum.Duration):
                if time_difference.in_hours() >= 100:
                    age_readable = f"{difference.in_days()}d"
                else:
                    age_readable = f"{difference.in_hours()}h"
                return age_readable

            # Convert last played time into a readable format like "10d" which means the player played ranked last 10 days ago
            last_played = int(api_entry["last_played"].strip("/Date()")) // 1000
            last_played = pendulum.from_timestamp(last_played) - pendulum.duration(hours=6) # Fix timezone offset as sc2unmasked doesnt seem to use UTC?
            difference = utc_time_now - last_played
            last_played_ago = format_time_readable(difference)

            # Convert the last streamed time into a readable format like above
            if api_entry["last_online"]:
                last_streamed = int(api_entry["last_online"].strip("/Date()")) // 1000
                last_streamed = pendulum.from_timestamp(last_streamed) - pendulum.duration(hours=6)
                difference = utc_time_now - last_streamed
                last_streamed_ago = format_time_readable(difference)
            else:
                last_streamed_ago = ""

            # Rank for gm, else tier for every other league
            rank_or_tier = api_entry["rank"] if api_entry["league"] == "grandmaster" else api_entry["tier"]

            formatted_result = [
                # Server, Race, League, MMR, Win/Loss, Name, Last Played, Last Streamed
                api_entry["server"].upper(),
                api_entry["race"].upper(),
                league_dict.get(api_entry["league"], "") + f"{rank_or_tier}",
                str(api_entry["mmr"]),
                f"{wins}-{losses}",
                full_display_name[:20], # Shorten for discord, unreadable if the discord window isnt wide enough
                f"{last_played_ago}",
                f"{last_streamed_ago}",
            ]
            return formatted_result

        if len(content_as_list) > 5:
            # TODO: CHILL OUT too many requests in one message
            return

        if not content_as_list:
            # Incorrect usage
            response_complete = f"{message.author.mention} correct usage:\n{trigger}mmr name\nor\n{trigger}mmr name1 name2 name3"
            await self.send_message(message.channel, response_complete)
            return
        else:
            # Correct usage
            for query_name in content_as_list:
                # It might fit 20 results in discord
                request_response = await requests.get(f"http://sc2unmasked.com/API/Player?q={query_name}&results=15")
                request_response_dict = await request_response.json()
                results = request_response_dict["players"]

                if not results:
                    # No player found
                    response.append(f"No player found with name `{query_name}`")
                else:
                    # Server, Race, League, MMR, Win/Loss, Name, Last Played, Last Streamed
                    fields = ["Serv", "R", "Leag", "MMR", "W/L", "Name", "LP", "LS"]
                    pretty_table = PrettyTable(field_names=fields)
                    pretty_table.border = False
                    for api_result in results:
                        formated_result = format_result(api_result)
                        pretty_table.add_row(formated_result)
                    query_link = f"<http://sc2unmasked.com/Search?q={query_name}>"
                    response_complete = f"{query_link}\n```md\nLP: Last Played, LS: Last Stream\n{len(results)} results for {query_name}:\n{pretty_table}```"
                    # print("Response complete:")
                    # print(response_complete)
                    await self.send_message(message.channel, response_complete)

        if response:
            response_as_str = "\n".join(response)
            response_complete = f"{message.author.mention}\n{response_as_str}"
            await self.send_message(message.channel, response_complete)


    async def _match_stream_name(self, streamer_name: str, stream_infos: List[dict]):
        matches = [stream_info for stream_info in stream_infos if  streamer_name.lower() in stream_info["channel"]["display_name"].lower()]
        return matches


    async def stream_get_uptime(self, streaminfo: dict) -> int:
        re_pattern = "([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z"
        # Has to work with "2019-01-05T13:17:30Z"
        re_compiled = re.compile(re_pattern)
        start_time = streaminfo["created_at"]
        results = re.findall(re_compiled, start_time)
        if results:
            results = results[0]
            start_time = pendulum.from_format(" ".join(results), fmt="YYYY MM DD HH mm ss")

            utc_timezone = pendulum.timezone("UTC")
            utc_time_now = pendulum.now(utc_timezone)

            return (utc_time_now - start_time).in_seconds()
        return 0


    async def _convert_uptime_to_readable(self, uptime_in_seconds: int) -> str:
        duration = pendulum.duration(seconds=uptime_in_seconds)
        return duration.in_words()


    async def _get_vod_with_timestamp(self, streamer_name: str, uptime_in_seconds: int) -> str:

        # https://api.twitch.tv/kraken/channels/rotterdam08/videos?broadcast_type=archive&limit=1&login=rotterdam08&client_id=
        url = f"https://api.twitch.tv/kraken/channels/{streamer_name}/videos?broadcast_type=archive&limit=1&login={streamer_name}&client_id={self.client_id}"
        response = await requests.get(f"{url}&client_id={self.client_id}")
        response_dict = await response.json()
        latest_vod_info = response_dict["videos"][0]
        latest_vod_url = latest_vod_info["url"]
        latest_vod_url_with_timestamp = f"{latest_vod_url}?t={uptime_in_seconds}s"
        return latest_vod_url_with_timestamp


    async def public_vod(self, message: discord.Message):
        """ This public command looks up a starcraft 2 twitch stream in the list of online streams, lists the current viewers and stream uptime, and if the stream is storing vods it will list the latest vod with the current timestamp
        Usage:
        !vod rotterdam08
        !vod rott """
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list = (await self._get_message_as_list(message))[1:]

        if not content_as_list:
            # Incorrect usage
            response_complete = f"{message.author.mention} correct usage:\n{trigger}vod name\nor\n{trigger}vod name1 name2 name3"
            await self.send_message(message.channel, response_complete)
            return
        if len(content_as_list) > 5:
            # TODO: CHILL OUT too many requests in one message
            return

        # Setup
        response_dict = {
            "streams": ["placeholder"],
            "_links": {
                "next": "https://api.twitch.tv/kraken/streams?game=StarCraft+II&limit=100&stream_type=live"
            }
        }

        streamer_dict = {
            streamer_name: "" for streamer_name in content_as_list
        }
        responses = []

        # Loop while stream name not found, might take a while on a game with many streams
        while len(response_dict["streams"]):
            next_url = response_dict["_links"]["next"]
            response = await requests.get(f"{next_url}&client_id={self.client_id}")
            response_dict = await response.json()

            for streamer_name, info in streamer_dict.items():
                if not info:
                    matches: List[dict] = await self._match_stream_name(streamer_name, response_dict["streams"])

                    if len(matches) > 1:
                        streamer_dict[streamer_name] = "Too many matches"
                        responses.append(f"Too many ({len(matches)}) streams found for stream name `{streamer_name}`")

                    elif len(matches) == 1:
                        match = matches[0]
                        stream_url: str = match["channel"]["url"]
                        stream_name: str = match["channel"]["display_name"]
                        # stream_title: str = match["channel"]["status"]
                        stream_uptime: int = await self.stream_get_uptime(match)
                        stream_uptime_readable: str = await self._convert_uptime_to_readable(stream_uptime)
                        stream_viewers: int = match["viewers"]
                        # stream_quality: int = match["video_height"]
                        # stream_fps: int = match["average_fps"]
                        try:
                            stream_vod_timestamp: str = await self._get_vod_with_timestamp(stream_name, stream_uptime)
                        except:
                            stream_vod_timestamp: str = "No past broadcasts available"

                        embed = discord.Embed(title=stream_name, url=stream_url)
                        embed.add_field(name="Uptime", value=stream_uptime_readable)
                        embed.add_field(name="Viewers", value=str(stream_viewers))
                        # embed.add_field(name="Quality", value=f"{stream_quality}p {stream_fps}fps")
                        embed.add_field(name="Vod Timestamp", value=stream_vod_timestamp)
                        # embed.add_field(name="Stream Title", value=stream_title)
                        await self.send_message(message.channel, "", embed=embed)
                        streamer_dict[streamer_name] = "Found"

        for streamer_name, info in streamer_dict.items():
            if info == "":
                responses.append(f"No livestream found for `{streamer_name}`")
        if responses:
            responses_as_str = "\n".join(responses)
            response_message = f"{responses_as_str}"
            await self.send_message(message.channel, response_message)


    async def list_public_commands(self):
        pass

if __name__ == "__main__":
    path = os.path.dirname(__file__)
    with open(os.path.join(path, "my_key.json")) as file:
        key = json.load(file)["key"]
    bot = Bot()
    bot.run(key)














