# Python Discord Sc2 Bot

Work in progress, bot is meant to be used privately


### Installation
- Install python 3.6 (32 or 64 bit)
- Run command `pip install -r requirements.txt` in this directory on the command line to install python requirements
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
- Type something in a channel the bot can see, and the bot will create a new `settings.json` file with the server's ID. Here you can edit the bot admins on that server locally if you can't access the bot (or just change `self.owner` in the `bot.py` file directly)

### Commands
**Admin commands:**
```markdown
# Allow the following roles to use the public commands
!addrole <role-name>
!delrole <role-name>

# Allow the following users to use admin commands
!addadmin <username>
!deladmin <username>
```

**Public commands:**
```markdown
# Uses the sc2unmasked api to find account names, clans, or streamer names and lists the result as a table in discord
!mmr <sc2-name>

# Uses the twitch api to find starcraft 2 streams on twitch (that are live) and find their latest vod with the timestamp
!vod <sc2-twitch-name>
```