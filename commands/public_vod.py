# https://pendulum.eustace.io/docs/
import pendulum
# https://discordpy.readthedocs.io/en/latest/api.html
import discord
import json, os, re
from typing import List, Dict, Set, Optional, Union, Iterable
import asyncio
from aiohttp_requests import requests
# http://zetcode.com/python/prettytable/
from prettytable import PrettyTable # pip install PTable
import traceback

from .base_class import BaseClass

class Vod(BaseClass):
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
        content_as_list: List[str] = (await self._get_message_as_list(message))[1:]

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

        streamer_dict: Dict[str, str] = {
            streamer_name: "" for streamer_name in content_as_list
        }
        responses = []
        vod_channels: Set[str] = set(await self._get_setting_server_value(message.server, "vod_channels", list))

        # Loop while stream name not found, might take a while on a game with many streams
        while len(response_dict["streams"]):
            next_url = response_dict["_links"]["next"]
            response = await requests.get(f"{next_url}&client_id={self.client_id}")
            response_dict = await response.json()

            for streamer_name, info in streamer_dict.items():
                if streamer_name.strip() == "":
                    # Fix double space: "test  test2".split(" ") == ["test", "", "test2"]
                    continue

                if not info: # If no info about the streamer was found yet
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

                        # Send the vod link also to the other channels
                        for channel in message.server.channels:
                            if channel.name in vod_channels:
                                await self.send_message(channel, "", embed=embed)

                        streamer_dict[streamer_name] = "Found"

        for streamer_name, info in streamer_dict.items():
            if info == "":
                responses.append(f"No livestream found for `{streamer_name}`")
        if responses:
            responses_as_str = "\n".join(responses)
            response_message = f"{responses_as_str}"
            await self.send_message(message.channel, response_message)


    async def admin_add_vod_channel(self, message: discord.Message):
        await self._admin_handle_vod_channel(message, remove_channel=False)


    async def admin_del_vod_channel(self, message: discord.Message):
        await self._admin_handle_vod_channel(message, remove_channel=True)


    async def _admin_handle_vod_channel(self, message: discord.Message, remove_channel=False):
        trigger = self.settings["servers"][message.server.id]["trigger"]
        message_content_as_list = (await self._get_message_as_list(message))[1:]

        if not message_content_as_list:
            # Incorrect usage
            response_complete = f"{message.author.mention} correct usage:\n{trigger}vodaddchannel channelname\nor\n{trigger}vodaddchannel channelname1 channelname2 channelname3"
            await self.send_message(message.channel, response_complete)
            return

        # vod_channels: List[str] = self.settings["servers"][message.server.id].get("vod_channels", [])
        vod_channels: List[str] = await self._get_setting_server_value(message.server, "vod_channels", list)
        server_channels: Iterable[discord.Channel] = message.server.channels

        responses = []
        settings_changed = False

        for channel_name in message_content_as_list:
            matches = [server_channel.name for server_channel in server_channels if channel_name.lower() == server_channel.name.lower() and server_channel.type == discord.ChannelType.text]
            if len(matches) > 1:
                responses.append(f"Found multiple matches ({len(matches)}) for channel name `{channel_name}`")
            elif len(matches) == 1:
                match = matches[0]
                exists = match in vod_channels
                if not remove_channel and exists:
                    # Vod channel already exists in list but wanted to add to list
                    responses.append(f"Channel `{channel_name}` already in vod channels")
                elif not remove_channel and not exists:
                    # Vod channel doesn't exist in list, add to list
                    vod_channels.append(match)
                    settings_changed = True
                    responses.append(f"Channel `{channel_name}` was added to vod channels ({len(vod_channels)})")
                elif remove_channel and not exists:
                    # Vod channel doesn't exist in list but wanted to remove
                    responses.append(f"Channel `{channel_name}` was not found in in vod channels")
                elif remove_channel and exists:
                    # Vod channel exists in list, remove it from list
                    vod_channels.remove(match)
                    settings_changed = True
                    responses.append(f"Channel `{channel_name}` was removed from vod channels ({len(vod_channels)})")

            else:
                responses.append(f"No match found for channel name `{channel_name}`")

        if settings_changed:
            await self.save_settings()

        if responses:
            responses_as_str = "\n".join(responses)
            response_message = f"{responses_as_str}"
            await self.send_message(message.channel, f"{message.author.mention}\n{response_message}")

