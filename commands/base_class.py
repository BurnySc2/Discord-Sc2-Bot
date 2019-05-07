# https://pendulum.eustace.io/docs/
import pendulum

# https://discordpy.readthedocs.io/en/latest/api.html
import discord
import json, os, re
from typing import List, Dict, Set, Optional, Union
import asyncio
from aiohttp_requests import requests

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
