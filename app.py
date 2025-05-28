from pyrogram import Client
from utils import LOGGER
from config import API_ID, API_HASH, BOT_TOKEN

LOGGER.info("Creating Bot Client From BOT_TOKEN")

app = Client(
    "SmartTools",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=1000,
    plugins=dict(root="plugins")  
)

LOGGER.info("Bot Client Created Successfully!")