import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import UserIdInvalid, PeerIdInvalid
from concurrent.futures import ThreadPoolExecutor
from config import ADMIN_IDS
from core import user_activity_collection
from utils import LOGGER


executor = ThreadPoolExecutor(max_workers=10)

@Client.on_message(filters.command("all") & filters.private)
async def all_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) executed /all command")

    if user_id not in ADMIN_IDS:
        await client.send_message(
            chat_id=message.chat.id,
            text="**❌ You are not authorized to use this command.**",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    async def get_all_balances():
        """Fetch balances for all users from user_activity_collection."""
        try:
            def sync_get_balances():
                return list(user_activity_collection.find({}, {"user_id": 1, "balance": 1, "_id": 0}))
            return await asyncio.get_event_loop().run_in_executor(executor, sync_get_balances)
        except Exception as e:
            LOGGER.error(f"Database error while fetching all user balances: {e}")
            return None

    # Fetch all user balances
    users = await get_all_balances()
    if users is None:
        await client.send_message(
            chat_id=message.chat.id,
            text="**❌ Failed to fetch user balances due to database error.**",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if not users:
        await client.send_message(
            chat_id=message.chat.id,
            text="**❌ No users found in the database.**",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Process user details and build response
    user_entries = []
    for user in users:
        user_id = user.get("user_id")
        balance = user.get("balance", 0)

        # Fetch user details
        try:
            user_obj = await client.get_users(user_id)
            user_full_name = f"{user_obj.first_name} {user_obj.last_name or ''}".strip()
            username_display = f"@{user_obj.username}" if user_obj.username else "N/A"
        except (UserIdInvalid, PeerIdInvalid):
            user_full_name = "Unknown"
            username_display = "N/A"
        except Exception as e:
            LOGGER.error(f"Error fetching user details for {user_id}: {e}")
            user_full_name = "Unknown"
            username_display = "N/A"

        user_entries.append(
            f"**✘ User ID:** `{user_id}`\n"
            f"**✘ Name:** `{user_full_name}`\n"
            f"**✘ Username:** `{username_display}`\n"
            f"**✘ Balance:** `{balance}` credits"
        )

    # Format response
    response = (
        f"**✘ All Users Balance Info ↯**\n"
        f"**✘ Total Users:** `{len(users)}`\n"
        f"**✘ Requested By:** `{full_name}`\n\n"
        + "\n\n".join(user_entries)
    )

    # Split response if too long (Telegram message limit: ~4096 characters)
    if len(response) <= 4000:
        await client.send_message(
            chat_id=message.chat.id,
            text=response,
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        # Split into chunks
        lines = response.splitlines()
        current_message = ""
        for line in lines:
            if len(current_message) + len(line) + 1 <= 4000:
                current_message += line + "\n"
            else:
                await client.send_message(
                    chat_id=message.chat.id,
                    text=current_message,
                    parse_mode=ParseMode.MARKDOWN
                )
                current_message = line + "\n"
        if current_message:
            await client.send_message(
                chat_id=message.chat.id,
                text=current_message,
                parse_mode=ParseMode.MARKDOWN
            )