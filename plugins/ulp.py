import os
import re
import asyncio
import time
import aiofiles
from urllib.parse import urlparse
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.enums import ParseMode
from pyrogram.errors import UserIdInvalid, PeerIdInvalid
from concurrent.futures import ThreadPoolExecutor
from config import ADMIN_IDS, COMMAND_PREFIX, DEVELOPER_ID
from core import user_activity_collection
from utils import LOGGER

# Thread pool for CPU-bound and synchronous tasks
executor = ThreadPoolExecutor(max_workers=10)

# Semaphore to limit concurrent file processing
FILE_PROCESSING_SEMAPHORE = asyncio.Semaphore(20)

# Dictionary to store user states and their files
user_states = {}

# Task queue and active tasks tracking
task_queue = asyncio.Queue()
active_tasks = {}
task_counter = 0

# Function to derive sitename from site_input
def derive_sitename(site_input):
    if '.' in site_input:
        parsed = urlparse(f"http://{site_input}" if not site_input.startswith(('http://', 'https://')) else site_input)
        domain = parsed.netloc.lower()
        parts = domain.split('.')
        if len(parts) > 2:
            domain = '.'.join(parts[-2:])
        sitename = domain.split('.')[0]
    else:
        sitename = site_input.lower()
    sitename = sitename.capitalize()
    sitename = re.sub(r'[<>:"/\\|?*]', '_', sitename)
    return sitename

# Function to extract search term from site_input
def extract_search_term(site_input):
    if '.' in site_input:
        parsed = urlparse(f"http://{site_input}" if not site_input.startswith(('http://', 'https://')) else site_input)
        domain = parsed.netloc.lower()
        parts = domain.split('.')
        if len(parts) > 2:
            domain = '.'.join(parts[-2:])
        return domain.split('.')[0]
    return site_input.lower()

# Function to check if identifier is relevant to target domain
def is_valid_identifier(identifier, target_domain):
    return target_domain.lower() in identifier.lower()

# Async function to check user balance
async def check_balance(user_id):
    if user_id in ADMIN_IDS:
        return True
    try:
        def sync_check_balance():
            user_doc = user_activity_collection.find_one({"user_id": user_id})
            return user_doc and user_doc.get("balance", 0) >= 1
        return await asyncio.get_event_loop().run_in_executor(executor, sync_check_balance)
    except Exception as e:
        LOGGER.error(f"Database error while checking balance for user {user_id}: {e}")
        return False

# Async function to deduct credit
async def deduct_credit(user_id):
    if user_id not in ADMIN_IDS:
        try:
            def sync_deduct_credit():
                user_activity_collection.update_one(
                    {"user_id": user_id},
                    {"$inc": {"balance": -1}},
                    upsert=True
                )
            await asyncio.get_event_loop().run_in_executor(executor, sync_deduct_credit)
        except Exception as e:
            LOGGER.error(f"Database error while deducting credit for user {user_id}: {e}")

# Async function to add credits
async def add_credits(user_id, amount):
    try:
        def sync_add_credits():
            user_activity_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"balance": amount}},
                upsert=True
            )
        await asyncio.get_event_loop().run_in_executor(executor, sync_add_credits)
        return True
    except Exception as e:
        LOGGER.error(f"Database error while adding credits for user {user_id}: {e}")
        return False

# Function to update queue status for all active tasks
async def update_queue_status():
    sorted_tasks = sorted(active_tasks.items(), key=lambda x: x[0])
    for index, (task_id, (user_id, processing_message)) in enumerate(sorted_tasks, 1):
        new_text = f"**Hey Bro Processing Logs To ULP**\n**Your request in Queue {index}/{len(active_tasks)}**"
        try:
            # Only edit if the new text is different from the current message text
            if processing_message.text != new_text:
                await processing_message.edit_text(
                    new_text,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            LOGGER.error(f"Error updating queue status for task {task_id}: {e}")

# Background task processor
async def process_tasks():
    while True:
        task, task_id, user_id, processing_message = await task_queue.get()
        try:
            active_tasks[task_id] = (user_id, processing_message)
            await update_queue_status()
            await task()
        except Exception as e:
            LOGGER.error(f"Error processing task {task_id}: {e}")
        finally:
            del active_tasks[task_id]
            await update_queue_status()
            task_queue.task_done()

# Start task processor
asyncio.create_task(process_tasks())

@Client.on_message(filters.command("feed") & filters.private)
async def feed_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) executed /feed command")
    
    if user_id != DEVELOPER_ID:
        await message.reply_text("**❌ Only the developer can use this command.**", parse_mode=ParseMode.MARKDOWN)
        return

    user_states[user_id] = {'state': 'waiting_for_files', 'files': []}
    await message.reply_text("**📥 Kindly Send Logs Here**", parse_mode=ParseMode.MARKDOWN)

@Client.on_message(filters.command("stop") & filters.private)
async def stop_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) executed /stop command")
    
    if user_id != DEVELOPER_ID:
        await message.reply_text("**❌ Only the developer can use this command.**", parse_mode=ParseMode.MARKDOWN)
        return

    if user_id not in user_states or user_states[user_id]['state'] != 'waiting_for_files':
        await message.reply_text("**❌ No files to process. Use /feed to start sending files.**", parse_mode=ParseMode.MARKDOWN)
        return

    loading_message = await message.reply_text("**✘ Starting Downloading Them.↯ **", parse_mode=ParseMode.MARKDOWN)
    downloaded_files = []
    total_files = len(user_states[user_id]['files'])

    async with FILE_PROCESSING_SEMAPHORE:
        for serial_number, file in enumerate(user_states[user_id]['files'], start=1):
            try:
                file_name = file['name']
                await loading_message.edit_text(f"**✘ Download Started `{file_name}` ↯ **", parse_mode=ParseMode.MARKDOWN)
                file_path = await client.download_media(
                    file['id'],
                    file_name=f"./downloads/{file_name}"
                )
                downloaded_files.append(file_path)
                await loading_message.edit_text(f"**✘ Downloaded: `{file_name}` ↯ **", parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(0.5)
            except Exception as e:
                await loading_message.edit_text(f"**❌ Error downloading `{file_name}`: {e}**", parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(1)

    user_states[user_id]['state'] = 'files_received'
    user_states[user_id]['files'] = downloaded_files
    await loading_message.edit_text(f"**✘ All files downloaded ({len(downloaded_files)} files)↯ **", parse_mode=ParseMode.MARKDOWN)
    await asyncio.sleep(1)
    await loading_message.delete()
    await message.reply_text(f"**✘ Download complete! {len(downloaded_files)} ✘**", parse_mode=ParseMode.MARKDOWN)

@Client.on_message(filters.command("ulp") & filters.private)
async def ulp_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    command_parts = message.text.split()
    site_input = command_parts[1].lower() if len(command_parts) > 1 else "none"
    LOGGER.info(f"User {user_id} ({full_name}) executed /ulp command for site {site_input}")

    # Validate command and prerequisites before enqueuing
    if len(command_parts) < 2:
        await message.reply_text("**❌ Please provide a site URL or keyword after the `/ulp` command (e.g., /ulp instagram.com).**", parse_mode=ParseMode.MARKDOWN)
        return

    if not await check_balance(user_id):
        await message.reply_text(
            "**❌ You don't have enough credits to use this command. Contact an admin to add credits.**\nContact @smraaz",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    download_dir = './downloads'
    if not os.path.exists(download_dir) or not any(f.endswith('.txt') for f in os.listdir(download_dir)):
        await message.reply_text("**❌ No text files found in downloads. Use /feed and /stop to upload files first.**", parse_mode=ParseMode.MARKDOWN)
        return

    async def process_ulp():
        output_dir = './output'
        os.makedirs(output_dir, exist_ok=True)

        target_domain = extract_search_term(site_input)
        processing_message = await message.reply_text("**Hey Bro Processing Logs To ULP...**", parse_mode=ParseMode.MARKDOWN)

        start_time = time.time()
        patterns = [
            re.compile(r"^(?:https?://|android://)[^\s:]+[:]([^:]+)[:](.+)$", re.MULTILINE),
            re.compile(r"^(?:https?://|android://)[^\s|]+\|([^|]+)\|(.+)$", re.MULTILINE),
            re.compile(r"^(?:https?://|android://)[^\s]+\s+([^\s]+)\s+(.+)$", re.MULTILINE),
            re.compile(r"^[^\s:]+[:]([^:]+)[:](.+)$", re.MULTILINE),
            re.compile(r"^[^\s|]+\|([^|]+)\|(.+)$", re.MULTILINE),
            re.compile(r"^[^\s]+\s+([^\s]+)\s+(.+)$", re.MULTILINE),
        ]

        credentials = []
        total_lines = 0

        async with FILE_PROCESSING_SEMAPHORE:
            for file_name in os.listdir(download_dir):
                file_path = os.path.join(download_dir, file_name)
                if os.path.isfile(file_path) and file_name.endswith('.txt'):
                    try:
                        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                            content = await file.read()
                    except UnicodeDecodeError:
                        async with aiofiles.open(file_path, 'r', encoding='latin1', errors='ignore') as file:
                            content = await file.read()

                    lines = content.splitlines()
                    total_lines += len(lines)

                    def process_file(lines, patterns, target_domain):
                        file_credentials = []
                        for line in lines:
                            for pattern in patterns:
                                match = pattern.match(line.strip())
                                if match:
                                    identifier = match.group(1)
                                    password = match.group(2).split()[0]
                                    if is_valid_identifier(identifier, target_domain):
                                        file_credentials.append(f"{identifier}:{password}")
                        return file_credentials

                    file_credentials = await asyncio.get_event_loop().run_in_executor(
                        executor, process_file, lines, patterns, target_domain
                    )
                    credentials.extend(file_credentials)
                    await update_queue_status()

        end_time = time.time()
        time_taken = end_time - start_time

        await processing_message.delete()

        if not credentials:
            await message.reply_text(f"**❌ No matching credentials found for the specified site: `{target_domain}`.**", parse_mode=ParseMode.MARKDOWN)
            return

        sitename = derive_sitename(site_input)
        output_file_path = os.path.join(output_dir, f"{sitename}.txt")
        async with aiofiles.open(output_file_path, 'w', encoding='utf-8', errors='ignore') as output_file:
            for cred in credentials:
                await output_file.write(cred + '\n')

        user_states[user_id] = user_states.get(user_id, {})
        user_states[user_id]['last_site_input'] = site_input

        await deduct_credit(user_id)
        try:
            def sync_get_balance():
                user_doc = user_activity_collection.find_one({"user_id": user_id})
                return user_doc.get("balance", 0) if user_doc else 0
            new_balance = await asyncio.get_event_loop().run_in_executor(executor, sync_get_balance)
            await message.reply_text(f"**✨ 1 credit deducted. Remaining credits: {new_balance}**", parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            await message.reply_text("**❌ Failed to fetch remaining credits due to database issue.**", parse_mode=ParseMode.MARKDOWN)
            LOGGER.error(f"Database error in ulp_command_handler: {e}")

        fetched_amount = len(credentials)
        total_entries = total_lines
        caption = (
            f"**✘ Info Extracted↯ **\n"
            f"**✘ Target Site: `{target_domain}` ↯ **\n"
            f"**✘ Fetched: `{fetched_amount}` ↯  **\n"
            f"**✘ Total Lines Processed: `{total_entries}` ↯ **\n"
            f"**✘ Time Taken: `{time_taken:.2f} seconds ↯ **\n"
            f"**✘ Requested By:** `{full_name}` ↯ "
        )

        reply_markup = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✘ NumPass ULP↯ ", callback_data="process_number"),
                InlineKeyboardButton("✘ MailPass ULP↯ ", callback_data="process_mail")
            ],
            [
                InlineKeyboardButton("✘ UserPass ULP↯ ", callback_data="process_user")
            ]
        ])

        await client.send_document(
            chat_id=message.chat.id,
            document=output_file_path,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            await client.send_document(
                chat_id="@ulpdrop",
                document=output_file_path,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            LOGGER.error(f"Failed to forward ULP document to @ulpdrop for user {user_id}: {e}")

    global task_counter
    task_counter += 1
    await task_queue.put((process_ulp, task_counter, user_id, await message.reply_text("**Hey Bro Processing Logs To ULP**", parse_mode=ParseMode.MARKDOWN)))

@Client.on_message(filters.document & filters.private)
async def document_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    file_name = message.document.file_name if message.document else "unknown"
    LOGGER.info(f"User {user_id} ({full_name}) sent document {file_name}")
    
    if user_id != DEVELOPER_ID:
        await message.reply_text("**❌ Only the developer can send files.**", parse_mode=ParseMode.MARKDOWN)
        return

    if user_id in user_states and user_states[user_id]['state'] == 'waiting_for_files':
        if message.document.file_name.endswith('.txt'):
            user_states[user_id]['files'].append({
                'id': message.document.file_id,
                'name': message.document.file_name
            })
            await message.reply_text("**📥 File received. Send more or use /stop to finish.**", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("**❌ Only TXT Logs Supported**", parse_mode=ParseMode.MARKDOWN)

@Client.on_message(filters.forwarded & filters.private)
async def forwarded_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) forwarded document {file_name}")
    
    if user_id != DEVELOPER_ID:
        await message.reply_text("**❌ Only the developer can forward files.**", parse_mode=ParseMode.MARKDOWN)
        return

    if user_id in user_states and user_states[user_id]['state'] == 'waiting_for_files':
        if message.document and message.document.file_name.endswith('.txt'):
            user_states[user_id]['files'].append({
                'id': message.document.file_id,
                'name': message.document.file_name
            })
            await message.reply_text("**📥 File received. Send more or use /stop to finish.**", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.reply_text("**❌ Please send or forward txt files.**", parse_mode=ParseMode.MARKDOWN)

@Client.on_message(filters.text & filters.private & ~filters.command(["feed", "stop", "ulp", "add"]))
async def generic_message_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) sent non-command message: {message.text}")
    
    await message.reply_text(
        "**🤔 Yo, that's not a command I know!**\n"
        "Try these:\n"
        "- `/feed` (dev only): Send log files\n"
        "- `/stop` (dev only): Finish uploading files\n"
        "- `/ulp <site>`: Process logs for a site\n"
        "- `/add <user_id> <amount>` (admin only): Add credits\n"
        "Need help? Ping @smraaz!",
        parse_mode=ParseMode.MARKDOWN
    )

async def filter_emails(content):
    def process_emails(content):
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        emails = []
        for line in content:
            parts = line.strip().split(':')
            if len(parts) >= 2 and email_pattern.match(parts[0]):
                emails.append(parts[0])
        return emails
    return await asyncio.get_event_loop().run_in_executor(executor, process_emails, content)

async def filter_email_pass(content):
    def process_email_pass(content):
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        email_passes = []
        for line in content:
            parts = line.strip().split(':')
            if len(parts) >= 2 and email_pattern.match(parts[0]):
                email_passes.append(f"{parts[0]}:{parts[1]}")
        return email_passes
    return await asyncio.get_event_loop().run_in_executor(executor, process_email_pass, content)

async def filter_user_pass(content):
    def process_user_pass(content):
        email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        number_pattern = re.compile(r'^\d+$')
        user_passes = []
        for line in content:
            parts = line.strip().split(':')
            if len(parts) >= 2:
                identifier = parts[0]
                if not email_pattern.match(identifier) and not number_pattern.match(identifier):
                    user_passes.append(f"{identifier}:{parts[1]}")
        return user_passes
    return await asyncio.get_event_loop().run_in_executor(executor, process_user_pass, content)

async def filter_number_pass(content):
    def process_number_pass(content):
        number_pattern = re.compile(r'^\d+$')
        number_passes = []
        for line in content:
            parts = line.strip().split(':')
            if len(parts) >= 2 and number_pattern.match(parts[0]):
                number_passes.append(f"{parts[0]}:{parts[1]}")
        return number_passes
    return await asyncio.get_event_loop().run_in_executor(executor, process_number_pass, content)

@Client.on_message(filters.command("add") & filters.private)
async def add_credits_command_handler(client: Client, message: Message):
    user_id = message.from_user.id
    full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) executed /add command")

    if user_id not in ADMIN_IDS:
        await message.reply_text("**❌ You are not authorized to use this command.**", parse_mode=ParseMode.MARKDOWN)
        return

    command_parts = message.text.split()
    if len(command_parts) != 3:
        await message.reply_text("**❌ Usage: /add <user_id> <amount>**", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        target_user_id = int(command_parts[1])
        amount = int(command_parts[2])
        if amount <= 0:
            await message.reply_text("**❌ Amount must be a positive number.**", parse_mode=ParseMode.MARKDOWN)
            return
    except ValueError:
        await message.reply_text("**❌ Invalid user ID or amount. Please provide valid numbers.**", parse_mode=ParseMode.MARKDOWN)
        return

    if await add_credits(target_user_id, amount):
        try:
            def sync_get_balance():
                user_doc = user_activity_collection.find_one({"user_id": target_user_id})
                return user_doc.get("balance", 0) if user_doc else amount
            new_balance = await asyncio.get_event_loop().run_in_executor(executor, sync_get_balance)
            await message.reply_text(
                f"**✘ Successfully added {amount} credits to user {target_user_id}. New balance: {new_balance}**",
                parse_mode=ParseMode.MARKDOWN
            )
            LOGGER.info(f"User {user_id} ({full_name}) added {amount} credits to user {target_user_id}. New balance: {new_balance}")
            try:
                user = await client.get_users(target_user_id)
                user_full_name = f"{user.first_name} {user.last_name or ''}".strip()
                notification_text = (
                    f"**✘ Hey Bro {user_full_name} New Credit Added  ↯**\n"
                    f"**✘ Currently Total Credits Left {new_balance} ↯**"
                )
                await client.send_message(
                    chat_id=target_user_id,
                    text=notification_text,
                    parse_mode=ParseMode.MARKDOWN
                )
            except (UserIdInvalid, PeerIdInvalid) as e:
                LOGGER.error(f"Failed to notify user {target_user_id}: Invalid user ID or bot blocked - {e}")
            except Exception as e:
                LOGGER.error(f"Unexpected error while notifying user {target_user_id}: {e}")
        except Exception as e:
            await message.reply_text("**❌ Failed to fetch new balance due to database issue.**", parse_mode=ParseMode.MARKDOWN)
            LOGGER.error(f"Database error in add_credits_command_handler: {e}")
    else:
        await message.reply_text("**❌ Failed to add credits due to database issue.**", parse_mode=ParseMode.MARKDOWN)

@Client.on_callback_query(filters.regex("process_number"))
async def process_number_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    full_name = f"{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) clicked process_number button")

    async def process_number():
        sitename = derive_sitename(user_states.get(user_id, {}).get('last_site_input', 'extracted_messages'))
        file_path = os.path.join('./output', f"{sitename}.txt")
        if not os.path.exists(file_path):
            await callback_query.message.reply_text(
                "**❌ No extracted messages file found. Please run /ulp first.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        async with FILE_PROCESSING_SEMAPHORE:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = await file.readlines()
            except UnicodeDecodeError:
                async with aiofiles.open(file_path, 'r', encoding='latin1', errors='ignore') as file:
                    content = await file.readlines()

            number_passes = await filter_number_pass(content)
            if not number_passes:
                await callback_query.message.reply_text(
                    "**❌ No valid number:password pairs found in the extracted messages.**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            user_full_name = f"{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}".strip()
            user_profile_url = f"https://t.me/{callback_query.from_user.username}" if callback_query.from_user.username else None
            user_link = f'<a href="{user_profile_url}">{user_full_name}</a>' if user_profile_url else user_full_name

            if len(number_passes) > 10:
                file_name = "ULP_Number_Pass_Results.txt"
                async with aiofiles.open(file_name, 'w', encoding='utf-8', errors='ignore') as f:
                    await f.write("\n".join(number_passes))
                caption = (
                    f"<b>✘ Here are the extracted number:password pairs:↯ </b>\n"
                    f"<b>✘━━━━━━━━━━━━━━━━↯ </b>\n"
                    f"<b>✘ Total Number:Pass:↯ </b> <code>{len(number_passes)}</code>\n"
                    f"<b>✘━━━━━━━━━━━━━━━━↯ </b>\n"
                    f"<b>✘ Filtered By:↯ </b> {user_link}\n"
                )
                await callback_query.message.reply_document(
                    document=file_name,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
                os.remove(file_name)
            else:
                formatted_number_passes = '\n'.join(f'`{number_pass}`' for number_pass in number_passes)
                await callback_query.message.reply_text(
                    f"**✘ Extracted Number:Password Pairs↯ **\n{formatted_number_passes}",
                    parse_mode=ParseMode.MARKDOWN
                )

    global task_counter
    task_counter += 1
    await task_queue.put((process_number, task_counter, user_id, await callback_query.message.reply_text("**Hey Bro Processing Logs To ULP**", parse_mode=ParseMode.MARKDOWN)))
    await callback_query.answer()

@Client.on_callback_query(filters.regex("process_mail"))
async def process_mail_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    full_name = f"{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) clicked process_mail button")

    async def process_mail():
        sitename = derive_sitename(user_states.get(user_id, {}).get('last_site_input', 'extracted_messages'))
        file_path = os.path.join('./output', f"{sitename}.txt")
        if not os.path.exists(file_path):
            await callback_query.message.reply_text(
                "**❌ No extracted messages file found. Please run /ulp first.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        async with FILE_PROCESSING_SEMAPHORE:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = await file.readlines()
            except UnicodeDecodeError:
                async with aiofiles.open(file_path, 'r', encoding='latin1', errors='ignore') as file:
                    content = await file.readlines()

            email_passes = await filter_email_pass(content)
            if not email_passes:
                await callback_query.message.reply_text(
                    "**❌ No valid email:password pairs found in the extracted messages.**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            user_full_name = f"{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}".strip()
            user_profile_url = f"https://t.me/{callback_query.from_user.username}" if callback_query.from_user.username else None
            user_link = f'<a href="{user_profile_url}">{user_full_name}</a>' if user_profile_url else user_full_name

            if len(email_passes) > 10:
                file_name = "ULP_Email_Pass_Results.txt"
                async with aiofiles.open(file_name, 'w', encoding='utf-8', errors='ignore') as f:
                    await f.write("\n".join(email_passes))
                caption = (
                    f"<b>✘ Here are the extracted email:password pairs:↯ </b>\n"
                    f"<b>✘━━━━━━━━━━━━━━━━↯ </b>\n"
                    f"<b>✘ Total Email:Pass:↯ </b> <code>{len(email_passes)}</code>\n"
                    f"<b>✘━━━━━━━━━━━━━━━━↯ </b>\n"
                    f"<b>✘ Filtered By:↯ </b> {user_link}\n"
                )
                await callback_query.message.reply_document(
                    document=file_name,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
                os.remove(file_name)
            else:
                formatted_email_passes = '\n'.join(f'`{email_pass}`' for email_pass in email_passes)
                await callback_query.message.reply_text(
                    f"**✘ Extracted Email:Password Pairs↯ **\n{formatted_email_passes}",
                    parse_mode=ParseMode.MARKDOWN
                )

    global task_counter
    task_counter += 1
    await task_queue.put((process_mail, task_counter, user_id, await callback_query.message.reply_text("**Hey Bro Processing Logs To ULP**", parse_mode=ParseMode.MARKDOWN)))
    await callback_query.answer()

@Client.on_callback_query(filters.regex("process_user"))
async def process_user_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    full_name = f"{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}".strip()
    LOGGER.info(f"User {user_id} ({full_name}) clicked process_user button")

    async def process_user():
        sitename = derive_sitename(user_states.get(user_id, {}).get('last_site_input', 'extracted_messages'))
        file_path = os.path.join('./output', f"{sitename}.txt")
        if not os.path.exists(file_path):
            await callback_query.message.reply_text(
                "**❌ No extracted messages file found. Please run /ulp first.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        async with FILE_PROCESSING_SEMAPHORE:
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = await file.readlines()
            except UnicodeDecodeError:
                async with aiofiles.open(file_path, 'r', encoding='latin1', errors='ignore') as file:
                    content = await file.readlines()

            user_passes = await filter_user_pass(content)
            if not user_passes:
                await callback_query.message.reply_text(
                    "**❌ No valid user:password pairs found in the extracted messages.**",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            user_full_name = f"{callback_query.from_user.first_name} {callback_query.from_user.last_name or ''}".strip()
            user_profile_url = f"https://t.me/{callback_query.from_user.username}" if callback_query.from_user.username else None
            user_link = f'<a href="{user_profile_url}">{user_full_name}</a>' if user_profile_url else user_full_name

            if len(user_passes) > 10:
                file_name = "ULP_User_Pass_Results.txt"
                async with aiofiles.open(file_name, 'w', encoding='utf-8', errors='ignore') as f:
                    await f.write("\n".join(user_passes))
                caption = (
                    f"<b>✘ Here are the extracted user:password pairs:↯ </b>\n"
                    f"<b>✘━━━━━━━━━━━━━━━━↯ </b>\n"
                    f"<b>✘ Total User:Pass:↯ </b> <code>{len(user_passes)}</code>\n"
                    f"<b>✘━━━━━━━━━━━━━━━━↯ </b>\n"
                    f"<b>✘ Filtered By:↯ </b> {user_link}\n"
                )
                await callback_query.message.reply_document(
                    document=file_name,
                    caption=caption,
                    parse_mode=ParseMode.HTML
                )
                os.remove(file_name)
            else:
                formatted_user_passes = '\n'.join(f'`{user_pass}`' for user_pass in user_passes)
                await callback_query.message.reply_text(
                    f"**✘ Extracted User:Password Pairs↯ **\n{formatted_user_passes}",
                    parse_mode=ParseMode.MARKDOWN
                )

    global task_counter
    task_counter += 1
    await task_queue.put((process_user, task_counter, user_id, await callback_query.message.reply_text("**Hey Bro Processing Logs To ULP**", parse_mode=ParseMode.MARKDOWN)))
    await callback_query.answer()