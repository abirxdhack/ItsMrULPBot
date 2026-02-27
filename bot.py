from telethon import TelegramClient

import config
from helpers.logger import LOGGER

ItsMrULPBot = TelegramClient(
    session='ItsMrULPBot',
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    connection_retries=None,
    retry_delay=1,
)


async def start_bot():
    LOGGER.info("Creating Bot Client from BOT_TOKEN")
    await ItsMrULPBot.start(bot_token=config.BOT_TOKEN)
    LOGGER.info("Bot Client Successfully created!")
