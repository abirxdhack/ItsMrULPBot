import re
import os
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from config import COMMAND_PREFIX

# Function to filter and fetch user:password pairs from file content
async def filter_user_pass(content):
    """Filter and fetch user:password pairs from the file content."""
    user_pass_pattern = re.compile(r'^[^|]+\|([^|@]+)\|(.+)$')
    user_passes = []
    for line in content:
        match = user_pass_pattern.match(line)
        if match:
            user = match.group(1)
            password = match.group(2).split()[0]  # Capture only the first part of the password
            user_passes.append(f"{user}:{password}")
    return user_passes

# Function to filter and fetch number:password pairs from file content
async def filter_number_pass(content):
    """Filter and fetch number:password pairs from the file content."""
    number_pass_pattern = re.compile(r'^[^|]+\|(\d+)\|(.+)$')
    number_passes = []
    for line in content:
        match = number_pass_pattern.match(line)
        if match:
            number = match.group(1)
            password = match.group(2).split()[0]  # Capture only the first part of the password
            number_passes.append(f"{number}:{password}")
    return number_passes

@Client.on_message(filters.command(["user"], prefixes=COMMAND_PREFIX) & filters.private)
async def handle_fuser_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document or not message.reply_to_message.document.file_name.endswith('.txt'):
        await client.send_message(message.chat.id, "<b>⚠️ Reply to a message with a text file.</b>", parse_mode=ParseMode.HTML)
        return

    temp_msg = await client.send_message(message.chat.id, "<b>⚡️ Filtering and Extracting User Pass...⏳</b>", parse_mode=ParseMode.HTML)
    file_path = await message.reply_to_message.download()

    with open(file_path, 'r') as file:
        content = file.readlines()

    user_passes = await filter_user_pass(content)
    if not user_passes:
        await temp_msg.delete()
        await client.send_message(message.chat.id, "<b>❌ No valid user:password pairs found in the file.</b>", parse_mode=ParseMode.HTML)
        os.remove(file_path)
        return

    user_full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    user_profile_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else None
    user_link = f'<a href="{user_profile_url}">{user_full_name}</a>' if user_profile_url else user_full_name

    if len(user_passes) > 10:
        file_name = "ULP_User_Pass_Results.txt"
        with open(file_name, 'w') as f:
            f.write("\n".join(user_passes))
        caption = (
            f"<b>Here are the extracted user:password pairs:</b>\n"
            f"<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>Total User:Pass:</b> <code>{len(user_passes)}</code>\n"
            f"<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>Filtered By:</b> {user_link}\n"
        )
        await temp_msg.delete()
        await client.send_document(message.chat.id, file_name, caption=caption, parse_mode=ParseMode.HTML)
        os.remove(file_name)
    else:
        formatted_user_passes = '\n'.join(f'`{user_pass}`' for user_pass in user_passes)
        await temp_msg.delete()
        await client.send_message(message.chat.id, formatted_user_passes, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    os.remove(file_path)

@Client.on_message(filters.command(["num"], prefixes=COMMAND_PREFIX) & filters.private)
async def handle_fnumber_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document or not message.reply_to_message.document.file_name.endswith('.txt'):
        await client.send_message(message.chat.id, "<b>⚠️ Reply to a message with a text file.</b>", parse_mode=ParseMode.HTML)
        return

    temp_msg = await client.send_message(message.chat.id, "<b>⚡️ Filtering and Extracting Number Pass...⏳</b>", parse_mode=ParseMode.HTML)
    file_path = await message.reply_to_message.download()

    with open(file_path, 'r') as file:
        content = file.readlines()

    number_passes = await filter_number_pass(content)
    if not number_passes:
        await temp_msg.delete()
        await client.send_message(message.chat.id, "<b>❌ No valid number:password pairs found in the file.</b>", parse_mode=ParseMode.HTML)
        os.remove(file_path)
        return

    user_full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    user_profile_url = f"https://t.me/{message.from_user.username}" if message.from_user.username else None
    user_link = f'<a href="{user_profile_url}">{user_full_name}</a>' if user_profile_url else user_full_name

    if len(number_passes) > 10:
        file_name = "ULP_Number_Pass_Results.txt"
        with open(file_name, 'w') as f:
            f.write("\n".join(number_passes))
        caption = (
            f"<b>Here are the extracted number:password pairs:</b>\n"
            f"<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>Total Number:Pass:</b> <code>{len(number_passes)}</code>\n"
            f"<b>━━━━━━━━━━━━━━━━</b>\n"
            f"<b>Filtered By:</b> {user_link}\n"
        )
        await temp_msg.delete()
        await client.send_document(message.chat.id, file_name, caption=caption, parse_mode=ParseMode.HTML)
        os.remove(file_name)
    else:
        formatted_number_passes = '\n'.join(f'`{number_pass}`' for number_pass in number_passes)
        await temp_msg.delete()
        await client.send_message(message.chat.id, formatted_number_passes, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
    os.remove(file_path)