import arrow
from datetime import timedelta

# https://discordpy.readthedocs.io/en/latest/api.html
import discord
import json, os, re
from typing import List, Dict, Set, Optional, Union
import asyncio
import aiohttp
from aiohttp_requests import requests

# http://zetcode.com/python/prettytable/
from prettytable import PrettyTable  # pip install PTable
import traceback

from .base_class import BaseClass


class Mmr(BaseClass):
    async def public_mmr(self, message: discord.Message):
        """ The public command '!mmr name', will look up an account name, clan name or stream name and list several results as a markdown table using PrettyTable
        Usage:
        !mmr twitch.tv/rotterdam08
        !mmr rotterdam
        !mmr [zelos] """
        trigger = self.settings["servers"][message.guild.id]["trigger"]
        content_as_list: List[str] = (await self._get_message_as_list(message))[1:]
        response = []

        if len(content_as_list) > 5:
            # TODO: CHILL OUT too many requests in one message
            return

        if not content_as_list:
            # Incorrect usage
            response_complete = (
                f"{message.author.mention} correct usage:\n{trigger}mmr name\nor\n{trigger}mmr name1 name2 name3"
            )
            await message.channel.send(response_complete)
            return
        else:
            # Correct usage
            for query_name in content_as_list:
                if query_name.strip() == "":
                    continue
                # It might fit 20 results in discord
                request_response = await requests.get(f"http://sc2unmasked.com/API/Player?q={query_name}&results=15")
                try:
                    request_response_dict = await request_response.json()
                except aiohttp.ContentTypeError:
                    # Error with aiohttp with decoding
                    response.append(f"Error while trying to decode JSON with input: `{query_name}`")
                    continue

                results = request_response_dict["players"]

                if not results:
                    # No player found
                    response.append(f"No player found with name `{query_name}`")
                else:
                    # Server, Race, League, MMR, Win/Loss, Name, Last Played, Last Streamed
                    fields = ["S-R-L", "MMR", "W/L", "LP", "LS", "Name"]
                    pretty_table = PrettyTable(field_names=fields)
                    pretty_table.border = False
                    for api_result in results:
                        formated_result = self.format_result(api_result)
                        pretty_table.add_row(formated_result)
                    query_link = f"<http://sc2unmasked.com/Search?q={query_name}>"
                    response_complete = f"{query_link}\n```md\nLP: Last Played, LS: Last Stream\n{len(results)} results for {query_name}:\n{pretty_table}```"
                    # print("Response complete:")
                    # print(response_complete)
                    await message.channel.send(response_complete)
                    # await self.send_message(message.channel, response_complete)

        if response:
            response_as_str = "\n".join(response)
            response_complete = f"{message.author.mention}\n{response_as_str}"
            await message.channel.send(response_complete)


    def format_result(self, api_entry):
        league_dict = {
            "grandmaster": "G",
            "master": "M",
            "diamond": "D",
            "platinum": "P",
            "gold": "G",
            "silver": "S",
            "bronze": "B",
        }
        # e.g. 2019-05-17T10:22:09.254655+00:00
        utc_time_now = arrow.utcnow()

        server = api_entry["server"].upper()
        race = api_entry["race"].upper()
        # Rank for gm, else tier for every other league
        rank_or_tier = api_entry["rank"] if api_entry["league"] == "grandmaster" else api_entry["tier"]
        league = league_dict.get(api_entry["league"], "") + f"{rank_or_tier}"

        clan_tag: str = api_entry["clan_tag"]
        account_name: str = api_entry["acc_name"]
        display_name: str = api_entry["display_name"]
        full_display_name = (
            (f"[{clan_tag}]" if clan_tag else "")
            + account_name
            + (f" ({display_name})" if display_name and display_name != account_name else "")
        )
        wins: int = api_entry["wins"]
        losses: int = api_entry["losses"]
        stream_name: str = api_entry["stream_name"]

        def format_time_readable(time_difference: timedelta):
            total_seconds: int = int(time_difference.total_seconds())
            if total_seconds // 3600 > 99:
                age_readable = f"{time_difference.days}d"
            else:
                age_readable = f"{total_seconds // 3600}h"
            return age_readable

        # Convert last played time into a readable format like "10d" which means the player played ranked last 10 days ago
        if api_entry["last_played"] is not None:
            last_played = int(api_entry["last_played"].strip("/Date()")) // 1000
            # e.g. last_played = 1550628565
            last_played_datetime = arrow.Arrow.utcfromtimestamp(last_played)
            # Fix timezone offset as sc2unmasked doesnt seem to use UTC?
            last_played_datetime_fixed = last_played_datetime.shift(hours=-7)
            # Get the difference
            difference: timedelta = utc_time_now - last_played_datetime_fixed
            last_played_ago = format_time_readable(difference)
        else:
            last_played_ago = ""

        # Convert the last streamed time into a readable format like above
        if api_entry["last_online"]:
            last_streamed = int(api_entry["last_online"].strip("/Date()")) // 1000
            if last_streamed < 0:
                last_streamed_ago = ""
            else:
                last_streamed_datetime = arrow.Arrow.utcfromtimestamp(last_streamed)
                last_streamed_datetime_fixed = last_streamed_datetime.shift(hours=-7)
                difference: timedelta = utc_time_now - last_streamed_datetime_fixed
                last_streamed_ago = format_time_readable(difference)
        else:
            last_streamed_ago = ""

        formatted_result = [
            # Server, Race, League, MMR, Win/Loss, Name, Last Played, Last Streamed
            f"{server} {race} {league}",
            str(api_entry["mmr"]),
            f"{wins}-{losses}",
            f"{last_played_ago}",
            f"{last_streamed_ago}",
            full_display_name[:18],  # Shorten for discord, unreadable if the discord window isnt wide enough
        ]
        return formatted_result