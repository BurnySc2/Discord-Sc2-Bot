from loguru import logger
import subprocess
import asyncio
from pathlib import Path
import sys

# https://github.com/samuelcolvin/watchgod
from watchgod import awatch, PythonWatcher

# Remove previous default handlers
logger.remove()
# Log to console
logger.add(sys.stdout, level="INFO")
# Log to file, max size 1 mb
logger.add("run.log", rotation="1 MB", level="INFO")


class BotRunner:
    def __init__(self):
        self.bot_process: subprocess.Popen = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.kill_bot()

    async def start_bot(self):
        current_folder = Path(__file__).parent
        bot_file_path = current_folder / "bot.py"
        command = f"/usr/local/bin/python3.7 -m poetry run python {bot_file_path.absolute()}"
        self.bot_process = subprocess.Popen(command.split(" "))
        logger.info(f"Starting bot on pid {self.bot_process.pid}")

    def kill_bot(self):
        if self.bot_process is not None and self.bot_process.poll() is not None:
            self.bot_process.kill()

    async def restart_bot(self):
        self.kill_bot()
        await self.start_bot()


async def file_watcher():
    """ Restart bot on .py file changes """
    logger.info("Started file watcher")
    async for changes in awatch(".", watcher_cls=PythonWatcher, normal_sleep=5000):
        logger.info(f"Restarting bot because of the following file changes: {changes}")
        await runner.restart_bot()


async def bot_restarter():
    """ If bot process is dead, restart """
    logger.info("Started bot restarter")
    while 1:
        await asyncio.sleep(5)
        if runner.bot_process is None or runner.bot_process.poll() is not None:
            logger.info(f"Restarting bot because it seems to have ended.")
            await runner.start_bot()


async def main():
    """
    Main entry point.
    Creates bot_restarter() and file_watcher() which run in a perma loop to restart the bot on file changes or when the bot has crashed
    """
    tasks = [asyncio.create_task(my_task) for my_task in [file_watcher(), bot_restarter()]]
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    with BotRunner() as runner:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
