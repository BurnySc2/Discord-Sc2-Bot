[![Actions Status](https://github.com/BurnySc2/Discord-Sc2-Bot/workflows/RunTests/badge.svg)](https://github.com/BurnySc2/Discord-Sc2-Bot/actions)

# DEPRECATED
Project has been moved to https://github.com/BurnySc2/monorepo

# Python Discord Sc2 Bot

Work in progress, bot is meant to be used privately


### Installation
- Install python 3.7 or newer (32 or 64 bit)
- Run commands 
    ```
    pip install poetry --user
    poetry install
    ``` 
  in this directory on the command line to install python requirements
- Go to [the discord developer portal](https://discordapp.com/developers/applications/), log in with your discord account and create an application
- Under `OAuth2` tab, set checkmark at `bot` and copy the authorization link into a new tab in your browser, select which server you want your bot to connect to (you have to be server admin on the discord server)
- Under `Bot` Tab, reveal your token and copy it
- Create a new `my_key.json` file in this bot folder, with contents 
    ```json
    {
        "key": "your-token-as-string"
    }
    ```
- Go to the [twitch dev portal](https://dev.twitch.tv/), log in with your twitch account, go to dashboard, view apps, register a new application with OAuth Redirect URL `http://localhost` and hit `Create`
- Now click `Manage` on the application, copy the `Cient ID`
- Create a new file called `my_client_id.json` in this bot folder and paste your client id into the field
    ```json
    {
        "client_id": "your_client_id"
    }
    ```
- You can now launch the bot.
- Add the bot to your discord server by going to the discord dev portal, click your bot, go to `OAuth2` tab and select the `bot` scope. Then open the newly generated link to connect it to a server. The link should look something like
    ```https://discordapp.com/api/oauth2/authorize?client_id=123123123123&permissions=0&scope=bot```
- Type something in a channel the bot can see, and the bot will create a new `settings.json` file with the server's ID. Here you can edit the bot admins on that server locally if you can't access the bot (or just change `self.owner` in the `bot.py` file directly)


### Running

Run the bot with command

`poetry run python run.py`

or if that doesn't work:

`python -m poetry run python run.py`


### Commands
**Public commands:**
```markdown
# Uses the sc2unmasked api to find account names, clans, or streamer names and lists the result as a table in discord
!mmr <sc2-name>

# Uses the twitch api to find starcraft 2 streams on twitch (that are live) and find their latest vod with the timestamp
!vod <sc2-twitch-name>

# Remind the user in a certain time in the same channel of a text message
!reminder <time> <message>

# Remind the user at a certain time in the same channel of a text message
!remindat <time> <message>

# List all active reminders of the user
!reminders

# Remove a reminder from !reminders
!delreminder <reminder-id>
```
