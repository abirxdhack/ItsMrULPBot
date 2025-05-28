import re
import os
from pyrogram import Client, filters
from pyrogram.enums import ParseMode, ChatType
from pyrogram.types import Message
from config import COMMAND_PREFIX

# Function to filter and fetch emails from file content
async def filter_emails(content):
    """Filter and fetch email addresses from the file content."""
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    patterns = [
        re.compile(r'^(?:https?://|android://)[^\s:]+[:|]([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[:|](.+)$', re.MULTILINE),
        re.compile(r'^(?:https?://|android://)[^\s:]+[:|]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s+(.+)$', re.MULTILINE),
    ]
    emails = []
    for line in content:
        for pattern in patterns:
            match = pattern.match(line.strip())
            if match and email_pattern.match(match.group(1)):
                emails.append(match.group(1))
    return emails

# Function to filter and fetch email:password pairs from file content
async def filter_email_pass(content):
    """Filter and fetch email:password pairs from the file content."""
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    patterns = [
        re.compile(r'^(?:https?://|android://)[^\s:]+[:|]([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})[:|](.+)$', re.MULTILINE),
        re.compile(r'^(?:https?://|android://)[^\s:]+[:|]?\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s+(.+)$', re.MULTILINE),
    ]
    email_passes = []
    for line in content:
        for pattern in patterns:
            match = pattern.match(line.strip())
            if match and email_pattern.match(match.group(1)):
                email = match.group(1)
                password = match.group(2).split()[0]  # Capture first part of password
                email_passes.append(f"{email}:{password}")
    return email_passes

@Client.on_message(filters.command(["email"], prefixes=COMMAND_PREFIX) & filters.private)
async def handle_fmail_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document or not message.reply_to_message.document.file_name.endswith('.txt'):
        await message.reply_text("**❌ Reply to a message with a valid text file.**", parse_mode=ParseMode.MARKDOWN)
        return

    temp_msg = await message.reply_text("**⚙️ Fetching and Filtering Emails...**", parse_mode=ParseMode.MARKDOWN)
    file_path = await message.reply_to_message.download()

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin1') as file:
            content = file.readlines()

    emails = await filter_emails(content)
    if not emails:
        await temp_msg.delete()
        await message.reply_text("**❌ No valid emails found in the file.**", parse_mode=ParseMode.MARKDOWN)
        os.remove(file_path)
        return

    if len(emails) > 10:
        file_name = "Emails_Results.txt"
        with open(file_name, 'w') as f:
            f.write("\n".join(emails))
        await temp_msg.delete()
        await client.send_document(message.chat.id, file_name, caption=f"**💥 Total Emails: `{len(emails)}`**", parse_mode=ParseMode.MARKDOWN)
        os.remove(file_name)
    else:
        await temp_msg.delete()
        formatted_emails = '\n'.join(f'`{email}`' for email in emails)
        await message.reply_text(f"**⭐️ Extracted Emails**\n{formatted_emails}", parse_mode=ParseMode.MARKDOWN)

    os.remove(file_path)

@Client.on_message(filters.command(["pass"], prefixes=COMMAND_PREFIX) & filters.private)
async def handle_fpass_command(client: Client, message: Message):
    if not message.reply_to_message or not message.reply_to_message.document or not message.reply_to_message.document.file_name.endswith('.txt'):
        await message.reply_text("**❌ Reply to a message with a valid text file.**", parse_mode=ParseMode.MARKDOWN)
        return

    temp_msg = await message.reply_text("**⚙️ Filtering and Extracting Email:Password Pairs...**", parse_mode=ParseMode.MARKDOWN)
    file_path = await message.reply_to_message.download()

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.readlines()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin1') as file:
            content = file.readlines()

    email_passes = await filter_email_pass(content)
    if not email_passes:
        await temp_msg.delete()
        await message.reply_text("**❌ No valid email:password pairs found in the file.**", parse_mode=ParseMode.MARKDOWN)
        os.remove(file_path)
        return

    if len(email_passes) > 10:
        file_name = "Email_Pass_Results.txt"
        with open(file_name, 'w') as f:
            f.write("\n".join(email_passes))
        await temp_msg.delete()
        await client.send_document(message.chat.id, file_name, caption=f"**💥 Total Pairs: `{len(email_passes)}`**", parse_mode=ParseMode.MARKDOWN)
        os.remove(file_name)
    else:
        await temp_msg.delete()
        formatted_email_passes = '\n'.join(f'`{email_pass}`' for email_pass in email_passes)
        await message.reply_text(f"**⭐️ Extracted Email:Password Pairs**\n{formatted_email_passes}", parse_mode=ParseMode.MARKDOWN)

    os.remove(file_path)