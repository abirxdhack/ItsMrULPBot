import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, Message
from pyrogram.enums import ParseMode
from app import app
from config import COMMAND_PREFIX, DEVELOPER_ID, UPDATES_CHANNEL
from core.mongo import user_activity_collection
from utils import LOGGER
from pymongo.errors import ConnectionFailure

# Define the start message with updated commands
START_MESSAGE = """
🌟 **Commands for this bot** 🌟

🛡️ **Admin Commands:**
⚙️ /feed 🚀 **To input data by forwarding files after command**
❌ /stop ✋ **To stop feeding data**
✨ /ulp keyword 🎯 **To generate ULP for keyword**
📧 /email **Reply to doc to extract Mail Pass Combo**
🔢 /num **Reply to doc to extract Number Pass Combo**
🔑 /pass **Reply to doc to extract User Pass Combo**
🗑️ /del **To delete all files**
📂 /db **To get uploaded logs and ULP files**

📈 **Explore and utilize these commands!** ✅
"""

# Define inline keyboard with buttons
inline_reply_markup = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("✘ʙᴏᴛ_ᴜᴘᴅᴀᴛᴇꜱ↯", url=UPDATES_CHANNEL),
        InlineKeyboardButton("✘ ᴍʏ_ᴅᴇᴠ ↯", user_id=DEVELOPER_ID)
    ]
])

# Define reply keyboard with buttons
reply_markup = ReplyKeyboardMarkup(
    [
        ["👤 Account", "💸 Balance"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Start command handler
@app.on_message(filters.command(["start"], prefixes=COMMAND_PREFIX) & filters.private)
async def start_message(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) executed /start command")
    
    try:
        # Send a direct message to the user with both inline and reply keyboards
        await client.send_photo(
            chat_id=user_id,
            photo="https://telegra.ph/file/36be820a8775f0bfc773e.jpg",
            caption=START_MESSAGE,
            reply_markup=inline_reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        # Send a separate message with the reply keyboard
        await client.send_message(
            chat_id=user_id,
            text="**✘ Choose an option below: ↯**",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        LOGGER.error(f"Failed to send start message for user {user_id}: {e}")
        await client.send_message(user_id, "**❌ Failed to send start message due to an error.**", parse_mode=ParseMode.MARKDOWN)

# Account button handler
@app.on_message(filters.regex(r"👤 Account") & filters.private)
async def account_button_handler(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) clicked Account button")
    
    username = user.username.lstrip('@') if user.username else "None"
    profile_link_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("✘Profile Link↯", user_id=user_id)]
    ])

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

    # Get current time in BST (UTC+6) for Last Chk
    bst_offset = datetime.timedelta(hours=6)
    current_time = datetime.datetime.now(datetime.timezone.utc) + bst_offset
    last_check = current_time.strftime("%I:%M %p » %d/%m/%Y BST")

    # Format the response using Markdown
    info_text = (
        "み Smart ULP Bot 💀  ↝ INFORMATION\n"
        "✘ ┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉↯\n"
        f"✘  **UID**           `{user_id}`↯\n"
        f"✘  **Name**         `{full_name}`↯\n"
        f"✘  **User**         `{username}`↯\n\n"
        "み Subscription Information\n"
        "✘ ┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉↯\n"
        f"✘  **Status**       `{status}`↯\n"
        f"✘  **Credits**      `{credits}`↯\n"
        f"✘  **Validity**     `{validity}`↯\n"
        f"✘  **Last Chk**     `{last_check}`↯\n"
        "✘ ┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉↯\n"
        f"✘  **DevBy**  ⌁  `@ISmartDevs`↯"
    )

    try:
        await client.send_message(user_id, info_text, reply_markup=profile_link_button, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(f"Error sending account info for user {user_id}: {e}")
        await client.send_message(user_id, "**❌ Sorry Could Not Find DB**", parse_mode=ParseMode.MARKDOWN)

# Balance button handler
@app.on_message(filters.regex(r"💸 Balance") & filters.private)
async def balance_button_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) clicked Balance button")
    
    # Fetch user balance from MongoDB
    try:
        user_doc = user_activity_collection.find_one({"user_id": user_id})
        credits = user_doc.get("balance", 0) if user_doc else 0
    except ConnectionFailure as e:
        LOGGER.error(f"Database connection error while fetching balance for user {user_id}: {e}")
        credits = 0

    # Format the response using Markdown
    balance_text = f"**💸 Your Current Credits: {credits} ↯**"

    try:
        await client.send_message(user_id, balance_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        LOGGER.error(f"Error sending balance info for user {user_id}: {e}")
        await client.send_message(user_id, "**❌ Sorry Could Not Find DB**", parse_mode=ParseMode.MARKDOWN)