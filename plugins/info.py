import datetime
import pytz
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode
from core import user_activity_collection
from utils import LOGGER
from pymongo.errors import ConnectionFailure

@Client.on_message(filters.command("info") & filters.private)
async def info_command_handler(client: Client, message: Message):
    """
    Handle the /info command to display user and subscription information.
    """
    user = message.from_user
    user_id = user.id
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    username = user.username.lstrip('@') if user.username else "None"

    # Fetch user balance from MongoDB
    try:
        user_doc = user_activity_collection.find_one({"user_id": user_id})
        credits = user_doc.get("balance", 0) if user_doc else 0
    except ConnectionFailure as e:
        LOGGER.error(f"Database connection error while fetching balance for user {user_id}: {e}")
        credits = 0

    # Determine subscription status and validity
    status = "PREMIUM" if credits > 0 else "FREE"
    validity = "Premium Subscription" if credits > 0 else "No Subscription"

    # Get current time in BDT (GMT+6) for Last Chk
    bdt_tz = pytz.timezone('Asia/Dhaka')
    current_time = datetime.datetime.now(bdt_tz)
    last_check = current_time.strftime("%I:%M %p » %d/%m/%Y BDT")

    # Format the response using Markdown
    info_text = (
        "み Smart ULP Bot 💀  ↝ INFORMATION\n"
        "✘┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉↯\n"
        f"✘ **UID**           `{user_id}` ↯\n"
        f"✘ **Name**         `{full_name}` ↯\n"
        f"✘ **User**         `{username}` ↯\n\n"
        "み Subscription Information\n"
        "✘┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉↯\n"
        f"✘ **Status**       `{status}` ↯\n"
        f"✘ **Credits**      `{credits}` ↯\n"
        f"✘ **Validity**     `{validity}` ↯\n"
        f"✘ **Last Chk**     `{last_check}` ↯\n"
        "✘┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n"
        f"✘ **DevBy**  ⌁  `@ISmartDevs`"
    )

    # Create InlineKeyboardButton for profile link
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✘Profile Link↯", user_id=user_id)]
    ])

    try:
        await message.reply_text(
            info_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        LOGGER.error(f"Error sending info message for user {user_id}: {e}")
        await message.reply_text(
            "**❌ Failed to display info due to an error.**",
            parse_mode=ParseMode.MARKDOWN
        )