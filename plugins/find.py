import re
import aiofiles
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import UserIdInvalid, PeerIdInvalid
from config import ADMIN_IDS, COMMAND_PREFIX
from utils import LOGGER

@Client.on_message(filters.command("find") & filters.private)
async def find_command_handler(client: Client, message: Message):
    """
    Admin-only command to find the sites a user has searched for using /ulp.
    Usage: /find <user_id> or /find <username> (with or without @).
    """
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    
    # Restrict to admins only
    if user_id not in ADMIN_IDS:
        LOGGER.info(f"User {user_id} ({full_name}) attempted /find but is not authorized")
        await message.reply_text("**❌ You are not authorized to use this command.**", parse_mode=ParseMode.MARKDOWN)
        return

    command_parts = message.text.split()
    if len(command_parts) < 2:
        LOGGER.info(f"User {user_id} ({full_name}) executed /find without arguments")
        await message.reply_text("**❌ Usage: /find <user_id> or /find <username>**", parse_mode=ParseMode.MARKDOWN)
        return

    target = command_parts[1].strip()
    target_user_id = None
    target_full_name = "Unknown"

    # Determine if the input is a user ID or username
    if target.startswith('@'):
        target = target[1:]  # Remove @ for username
        username = target
    else:
        # Try to parse as user ID first
        try:
            target_user_id = int(target)
            username = None
        except ValueError:
            username = target
            target_user_id = None

    # Resolve username to user ID if provided
    if username:
        try:
            user = await client.get_users(username)
            target_user_id = user.id
            target_full_name = f"{user.first_name} {user.last_name or ''}".strip()
        except (UserIdInvalid, PeerIdInvalid) as e:
            LOGGER.error(f"User {user_id} ({full_name}) executed /find for username {username} but user not found: {e}")
            await message.reply_text(f"**❌ User @{username} not found.**", parse_mode=ParseMode.MARKDOWN)
            return
        except Exception as e:
            LOGGER.error(f"Unexpected error while resolving username {username}: {e}")
            await message.reply_text("**❌ Failed to resolve username due to an error.**", parse_mode=ParseMode.MARKDOWN)
            return
    else:
        # Fetch full name for user ID
        try:
            user = await client.get_users(target_user_id)
            target_full_name = f"{user.first_name} {user.last_name or ''}".strip()
        except (UserIdInvalid, PeerIdInvalid) as e:
            LOGGER.error(f"User {user_id} ({full_name}) executed /find for user ID {target_user_id} but user not found: {e}")
            await message.reply_text(f"**❌ User ID {target_user_id} not found.**", parse_mode=ParseMode.MARKDOWN)
            return
        except Exception as e:
            LOGGER.error(f"Unexpected error while fetching user {target_user_id}: {e}")
            await message.reply_text("**❌ Failed to fetch user details due to an error.**", parse_mode=ParseMode.MARKDOWN)
            return

    LOGGER.info(f"User {user_id} ({full_name}) executed /find for user {target_user_id} ({target_full_name})")

    # Parse botlog.txt to find /ulp searches
    log_file = "botlog.txt"
    search_history = []
    log_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - INFO - User (\d+) \(([^)]+)\) executed /ulp command for site (\S+)"
    )

    try:
        async with aiofiles.open(log_file, 'r', encoding='utf-8') as file:
            async for line in file:
                match = log_pattern.match(line.strip())
                if match:
                    timestamp, log_user_id, log_full_name, site = match.groups()
                    if int(log_user_id) == target_user_id:
                        search_history.append((site, timestamp))
    except FileNotFoundError:
        LOGGER.error(f"Log file {log_file} not found for /find by user {user_id}")
        await message.reply_text("**❌ Log file not found. No search history available.**", parse_mode=ParseMode.MARKDOWN)
        return
    except UnicodeDecodeError:
        LOGGER.error(f"Failed to decode log file {log_file} with utf-8 for /find by user {user_id}")
        await message.reply_text("**❌ Failed to read log file due to encoding issue.**", parse_mode=ParseMode.MARKDOWN)
        return
    except Exception as e:
        LOGGER.error(f"Unexpected error while reading log file {log_file} for /find by user {user_id}: {e}")
        await message.reply_text("**❌ Failed to read log file due to an error.**", parse_mode=ParseMode.MARKDOWN)
        return

    if not search_history:
        await message.reply_text(
            f"**❌ No search history found for user {target_user_id} ({target_full_name}).**",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Format the search history
    history_lines = [f"- `{site}` (at {timestamp})" for site, timestamp in search_history]
    history_text = "\n".join(history_lines)
    response = (
        f"**✘ Search History for {target_user_id} ({target_full_name}) ↯**\n"
        f"**✘ Searched Sites: ↯**\n"
        f"{history_text}\n"
        f"**✘ Total Searches: {len(search_history)} ↯**"
    )

    await message.reply_text(response, parse_mode=ParseMode.MARKDOWN)