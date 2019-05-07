# https://pendulum.eustace.io/docs/
import pendulum

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
        trigger = self.settings["servers"][message.server.id]["trigger"]
        content_as_list: List[str] = (await self._get_message_as_list(message))[1:]
        response = []

        def format_result(api_entry):
            league_dict = {
                "grandmaster": "G",
                "master": "M",
                "diamond": "D",
                "platinum": "P",
                "gold": "G",
                "silver": "S",
                "bronze": "B",
            }
            utc_timezone = pendulum.timezone("Etc/GMT0")
            utc_time_now = pendulum.now(utc_timezone)

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

            def format_time_readable(time_difference: pendulum.Duration):
                if time_difference.in_hours() >= 100:
                    age_readable = f"{difference.in_days()}d"
                else:
                    age_readable = f"{difference.in_hours()}h"
                return age_readable

            # Convert last played time into a readable format like "10d" which means the player played ranked last 10 days ago
            if api_entry["last_played"] is not None:
                last_played = int(api_entry["last_played"].strip("/Date()")) // 1000
                # TODO: instead of 6 hours, use set timezone instead: dt.set(tz='Etc/GMT-6')
                last_played = pendulum.from_timestamp(last_played) - pendulum.duration(
                    hours=6
                )  # Fix timezone offset as sc2unmasked doesnt seem to use UTC?
                difference = utc_time_now - last_played
                last_played_ago = format_time_readable(difference)
            else:
                last_played_ago = ""

            # Convert the last streamed time into a readable format like above
            if api_entry["last_online"]:
                last_streamed = int(api_entry["last_online"].strip("/Date()")) // 1000
                if last_streamed < 0:
                    last_streamed_ago = ""
                else:
                    last_streamed = pendulum.from_timestamp(last_streamed) - pendulum.duration(hours=6)
                    difference = utc_time_now - last_streamed
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

        if len(content_as_list) > 5:
            # TODO: CHILL OUT too many requests in one message
            return

        if not content_as_list:
            # Incorrect usage
            response_complete = (
                f"{message.author.mention} correct usage:\n{trigger}mmr name\nor\n{trigger}mmr name1 name2 name3"
            )
            await self.send_message(message.channel, response_complete)
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
