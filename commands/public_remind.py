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

class Remind(BaseClass):
    def __init__(self):
        super().__init__()
        self.reminders = {}
        """
        Has the following structure:
        {
            "user_id": [
                {
                    user_name: username of person who wanted to be reminded,
                    remind_message_id: message id of the message that was sent in server channel to remind (so that later we can react with a checkbox when the remind was complete,
                    remind_message_channel_id: in which channel the message above was sent in
                    remind_text: my reminder text,
                    remind_time: the seconds timestamp which pendulum can parse,
                }
            ]
        }
        """
        self.reminder_limit = 10


    async def _get_all_reminders_by_user(self, user: discord.Member) -> list:
        if user.id not in self.reminders:
            self.reminders[user.id] = []
        return self.reminders[user.id]


    async def _get_correct_remind_in_usage_text(self, message: discord.Message) -> str:
        trigger = self.settings["servers"][message.server.id]["trigger"]
        return f"Correct usage: `{trigger}remindin hours`, `{trigger}remindin h:mm`, `{trigger}remindin h:mm:ss`, `{trigger}remindin days h:mm:ss`"


    async def _get_duration_now_to_timestamp(self, timestamp: int) -> pendulum.Duration:
        reminder_time = pendulum.from_timestamp(timestamp)
        time_now = pendulum.now("GMT+0")
        duration: pendulum.Duration = reminder_time - time_now
        return duration


    async def _clean_reminders(self):
        removed_a_reminder = False
        for user_id in list(self.reminders):
            reminders = self.reminders[user_id]
            member = next((user for user in self.get_all_members() if user.id == user_id), None)
            if member:
                for reminder in reminders[:]:
                    duration = await self._get_duration_now_to_timestamp(reminder["remind_time"])
                    if duration.total_seconds() < 0:
                        removed_a_reminder = True
                        reminders.remove(reminder)
            if len(reminders) == 0:
                self.reminders.pop(user_id)
                removed_a_reminder = True
        if removed_a_reminder:
            await self.save_reminders()


    async def _add_reminder_for_user(self, message: discord.Message, duration: pendulum.Duration, remind_text: str):
        time_now = pendulum.now("GMT+0")
        time_future: pendulum.DateTime = time_now + duration
        time_stamp = time_future.int_timestamp

        time_human_readable = time_future.to_rss_string()
        duration_human_readable = duration.in_words("en")

        await self.add_reaction(message, emoji="⏰")

        total_remind_text = f" with text: `{remind_text}`" if remind_text else ""
        response = f"{message.author.mention} reminding you on `{time_human_readable}` which is in `{duration_human_readable}`{total_remind_text}"

        sent_message: discord.Message = await self.send_message(message.channel, response)
        user_reminders = await self._get_all_reminders_by_user(message.author)

        user_reminders.append({
            "user_name": str(message.author),
            "remind_message_id": sent_message.id, # string
            "remind_message_channel_id": sent_message.channel.id, # string
            "remind_text": remind_text,
            "remind_time": time_stamp,
        })
        await self.save_reminders()
        await self.start_reminder(message.author, duration, sent_message.id)


    async def start_reminder(self, user: discord.Member, duration: pendulum.Duration, remind_message_id: str):
        await asyncio.sleep(duration.total_seconds())

        if user.id in self.reminders:
            user_reminders = await self._get_all_reminders_by_user(user)
            for reminder in user_reminders:
                if reminder["remind_message_id"] == remind_message_id:
                    # Message wasn't deleted or aborted, so send reminder
                    remind_text: str = reminder["remind_text"]
                    remind_text_total = f"Reminder: `{remind_text}`" if remind_text.strip() else "Remind!"
                    await self.send_message(user, f"{remind_text_total}")
                    old_remind_message_channel = self.get_channel(reminder["remind_message_channel_id"])
                    old_remind_message = await self.get_message(old_remind_message_channel, reminder["remind_message_id"])
                    user_reminders.remove(reminder)
                    await self.save_reminders()
                    # Verify on the old reminder message that the remind was successful
                    await self.add_reaction(old_remind_message, emoji="✅")


    async def start_reminders(self):
        await self._clean_reminders()
        for user_id in list(self.reminders):
            reminders = self.reminders[user_id]
            member = next((user for user in self.get_all_members() if user.id == user_id), None)
            if member:
                for reminder in reminders[:]:
                    duration = await self._get_duration_now_to_timestamp(reminder["remind_time"])
                    if duration.total_seconds() > 0:
                        await self.start_reminder(member, duration, reminder["remind_message_id"])


    async def public_remind_in(self, message: discord.Message):
        trigger = self.settings["servers"][message.server.id]["trigger"]
        message_content_as_list = (await self._get_message_as_list(message))[1:]
        # message_content = " ".join(message_content_as_list)

        responses = []

        try:
            days = 0
            has_days_argument = False

            if len(message_content_as_list) == 0:
                # Wrong usage
                response = await self._get_correct_remind_in_usage_text(message)
                await self.send_message(message.channel, f"{message.author.mention} {response}")
                return

            elif len(message_content_as_list) >= 2:
                try:
                    parsed_time: pendulum.DateTime = pendulum.parse(message_content_as_list[1], strict=False)
                    days = int(message_content_as_list[0])
                    has_days_argument = True
                except:
                    # Will respond with an error message if the first argument can't be parsed
                    pass

            if has_days_argument:
                time = message_content_as_list[1]
                remind_text = message_content_as_list[2:]
            else:
                time = message_content_as_list[0]
                remind_text = message_content_as_list[1:]


            parsed_time: pendulum.DateTime = pendulum.parse(time, strict=False)
            time_now = parsed_time
            time_now = time_now.set(hour=0, minute=0, second=0, microsecond=0)
            parsed_time = parsed_time.add(days=days)
            duration: pendulum.Duration = parsed_time - time_now
            if duration.total_seconds() <= 0:
                # Has to be in future
                responses.append(f"{message.author.mention} your reminder must be in the future!")
            else:
                reminders_amount = len(await self._get_all_reminders_by_user(message.author))
                if reminders_amount < self.reminder_limit:
                    # Set reminder
                    remind_text_str = " ".join(remind_text)
                    await self._add_reminder_for_user(message, duration=duration, remind_text=remind_text_str)
                else:
                    # Too many reminders
                    responses.append(f"{message.author.mention} you currently have {reminders_amount} reminders and the maximum amount of reminders per user is {self.reminder_limit}")

        except Exception as e:
            # Couldn't parse the given time string
            message_content = " ".join(message_content_as_list)
            responses.append(f"{message.author.mention} unable to parse `{message_content}`")
            responses.append(await self._get_correct_remind_in_usage_text(message))

        if responses:
            response_complete = "\n".join(responses)
            await self.send_message(message.channel, response_complete)


    async def public_remind_at(self, message: discord.Message):
        pass


    async def public_list_reminders(self, message: discord.Message):
        """ List all of the user's reminders """
        await self._clean_reminders()
        trigger = self.settings["servers"][message.server.id]["trigger"]
        reminders = await self._get_all_reminders_by_user(message.author)

        time_now = pendulum.now("GMT+0")
        responses = []

        if len(reminders) == 0:
            # Has no reminders
            responses.append(f"{message.author.mention} you currently have no reminders")
        else:
            responses.append(f"{message.author.mention} your reminders are:")
            for count, reminder in enumerate(reminders):
                duration = await self._get_duration_now_to_timestamp(reminder["remind_time"])
                reminder_time: pendulum.DateTime = (time_now + duration)
                reminder_time_readable = reminder_time.to_rss_string()
                reminder_duration_readable = duration.in_words("en")

                reminder_text = reminder["remind_text"]
                reminder_text_total = f" with reminder text: `{reminder_text}`" if reminder_text else f""
                responses.append(f"{1+count}: On `{reminder_time_readable}` which is in `{reminder_duration_readable}`{reminder_text_total}")
            responses.append(f"You can remove reminders by typing: {trigger}delremind <number>")

        if responses:
            response_complete = "\n".join(responses)
            await self.send_message(message.channel, response_complete)


    async def public_del_remind(self, message: discord.Message):
        """ Removes reminders from the user """
        await self._clean_reminders()
        trigger = self.settings["servers"][message.server.id]["trigger"]
        message_content_as_list = (await self._get_message_as_list(message))[1:]
        reminders = await self._get_all_reminders_by_user(message.author)
        time_now = pendulum.now("GMT+0")
        responses = []

        if not reminders:
            # Has no reminders
            responses.append(f"{message.author.mention} you currently have no reminders")

        if reminders and message_content_as_list:
            for number in message_content_as_list:
                try:
                    index = int(number)
                except:
                    # Incorrect argument
                    responses.append(f"{message.author.mention} unable to parse {number}")
                    break # Should be continue if we are parsing multiple reminders per command

                try:
                    reminder = reminders.pop(index-1)
                    await self.save_reminders()

                    duration = await self._get_duration_now_to_timestamp(reminder["remind_time"])
                    reminder_time: pendulum.DateTime = (time_now + duration)
                    reminder_time_readable = reminder_time.to_rss_string()
                    reminder_duration_readable = duration.in_words("en")
                    responses.append(f"{message.author.mention} removing reminder which was set on {reminder_time_readable} which is in {reminder_duration_readable}")
                except:
                    # Reminder with that index doesn't exist
                    responses.append(f"{message.author.mention} you only have {len(reminders)} reminders")
                    pass
                # Only remove one reminder per command
                break

        elif not message_content_as_list:
            # Wrong usage
            responses.append((await self._get_correct_remind_in_usage_text(message)))

        if responses:
            response_complete = "\n".join(responses)
            await self.send_message(message.channel, response_complete)







