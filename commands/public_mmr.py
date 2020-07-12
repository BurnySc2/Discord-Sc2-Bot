import arrow
from datetime import timedelta
from dataclasses import dataclass

# https://discordpy.readthedocs.io/en/latest/api.html
import discord
import json, os, re
from typing import List, Dict, Set, Optional, Union
import asyncio
import aiohttp

# http://zetcode.com/python/prettytable/
from prettytable import PrettyTable  # pip install PTable
import traceback


from .base_class import BaseClass


@dataclass()
class Sc2LadderResult:
    realm: int
    # One of US, EU, KR
    region: str
    # One of Master GrandMaster etc
    rank: str
    username: str
    # Battle tag with #number
    bnet_id: str
    # One of Zerg Terran Protoss Random
    race: str
    mmr: int
    wins: int
    losses: int
    # Clantag or None if not given
    clan: Optional[str]
    profile_id: int
    alias: Optional[str]

    @property
    def short_race(self) -> str:
        return self.race[0]

    @property
    def short_league(self):
        league_dict = {
            "grandmaster": "G",
            "master": "M",
            "diamond": "D",
            "platinum": "P",
            "gold": "G",
            "silver": "S",
            "bronze": "B",
        }
        return league_dict[self.rank.lower()]

    def format_result(self) -> List[str]:
        return [
            f"{self.region} {self.short_race} {self.short_league}",
            f"{self.mmr}",
            f"{self.wins}-{self.losses}",
            f"{self.username[:18]}",
            f"{self.alias[:18] if self.alias else ''}",
        ]


class Mmr(BaseClass):
    async def public_mmr(self, message: discord.Message):
        """ The public command '!mmr name', will look up an account name, clan name or stream name and list several results as a markdown table using PrettyTable
        Usage:
        !mmr twitch.tv/rotterdam08
        !mmr rotterdam
        !mmr [zelos] """
        trigger: str = await self._get_setting_server_value(message.guild, "trigger")
        # trigger = self.settings["servers"][str(message.guild.id)]["trigger"]
        content_as_list: List[str] = (await self._get_message_as_list(message))[1:]
        responses = []

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
            async with aiohttp.ClientSession() as session:
                for query_name in content_as_list:
                    if query_name.strip() == "":
                        continue
                    # It might fit 15 results in discord
                    url = f"https://www.sc2ladder.com/api/player?query={query_name}&results=15"
                    async with session.get(url) as response:
                        if response.status != 200:
                            responses.append(f"Error: Status code `{response.status}` for query `{query_name}`")
                            continue
                        try:
                            results = await response.json()
                        except aiohttp.ContentTypeError:
                            # Error with aiohttp with decoding
                            responses.append(f"Error while trying to decode JSON with input: `{query_name}`")
                            continue

                        if not results:
                            # No player found
                            responses.append(f"No player found with name `{query_name}`")
                        else:
                            # Server, Race, League, MMR, Win/Loss, Name, Last Played, Last Streamed
                            fields = ["S-R-L", "MMR", "W/L", "Username", "Alias"]
                            pretty_table = PrettyTable(field_names=fields)
                            pretty_table.border = False
                            for api_result in results:
                                result_object = Sc2LadderResult(**api_result)
                                formated_result = result_object.format_result()
                                pretty_table.add_row(formated_result)
                            query_link = f"<https://www.sc2ladder.com/search?query={query_name}>"
                            response_complete = (
                                f"{query_link}\n```md\n{len(results)} results for {query_name}:\n{pretty_table}```"
                            )
                            # print("Response complete:")
                            # print(response_complete)
                            await message.channel.send(response_complete)
                            # await self.send_message(message.channel, response_complete)

        if responses:
            response_as_str = "\n".join(responses)
            response_complete = f"{message.author.mention}\n{response_as_str}"
            await message.channel.send(response_complete)
