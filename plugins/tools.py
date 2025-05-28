import os
import shutil
import re
import psutil
import platform
import subprocess
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS

# Helper function to convert speed to human-readable format
def speed_convert(size: float, is_mbps: bool = False) -> str:
    if is_mbps:
        return f"{size:.2f} Mbps"
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}bps"

# Helper function to convert bytes to human-readable file size
def get_readable_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024:
        return f"{size_in_bytes} B"
    power = 1024
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size_in_bytes >= power:
        size_in_bytes /= power
        n += 1
    return f"{size_in_bytes:.2f} {power_labels[n]}"

# Function to perform speed test
def run_speedtest():
    try:
        result = subprocess.run(["speedtest-cli", "--secure", "--json"], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception("Speedtest failed.")
        data = json.loads(result.stdout)
        return data
    except Exception as e:
        return {"error": str(e)}

# Async function to handle speed test logic
async def run_speedtest_task():
    with ThreadPoolExecutor() as pool:
        try:
            result = await asyncio.get_running_loop().run_in_executor(pool, run_speedtest)
            return result
        except Exception as e:
            return {"error": str(e)}

@Client.on_message(filters.command("del") & filters.user(ADMIN_IDS))
async def delete_command_handler(client, message: Message):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✘Logs Directory↯", callback_data="del_logs")],
        [InlineKeyboardButton("✘ULP Directory↯", callback_data="del_ulp")]
    ])
    await client.send_message(message.from_user.id, "Ok Sir, Please Kindly Choose The Directory", reply_markup=reply_markup)

@Client.on_callback_query(filters.regex(r"del_(logs|ulp)") & filters.user(ADMIN_IDS))
async def delete_callback_handler(client, callback_query):
    directory_type = callback_query.data.split("_")[1]
    download_dir = './downloads' if directory_type == "logs" else './output'
    
    loading_message = await client.send_message(callback_query.from_user.id, "**✘ Deleting files...↯**")
    
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
        os.makedirs(download_dir)
        await loading_message.delete()
        await client.send_message(callback_query.from_user.id, f"**✅ {directory_type.capitalize()} directory and files deleted.**")
    else:
        await loading_message.delete()
        await client.send_message(callback_query.from_user.id, f"**❌ {directory_type.capitalize()} directory does not exist.**")
    
    await callback_query.answer()

@Client.on_message(filters.command("db") & filters.user(ADMIN_IDS))
async def files_command_handler(client, message: Message):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✘Logs Directory↯", callback_data="db_logs_1")],
        [InlineKeyboardButton("✘ULP Directory↯", callback_data="db_ulp_1")]
    ])
    await client.send_message(message.from_user.id, "Ok Sir, Please Kindly Choose The Directory", reply_markup=reply_markup)

@Client.on_callback_query(filters.regex(r"db_(logs|ulp)_(\d+)") & filters.user(ADMIN_IDS))
async def files_page_callback_handler(client, callback_query):
    match = re.search(r"db_(logs|ulp)_(\d+)", callback_query.data)
    directory_type = match.group(1)
    page = int(match.group(2))
    
    download_dir = './downloads' if directory_type == "logs" else './output'
    files_per_page = 5

    if not os.path.exists(download_dir):
        await callback_query.message.edit_text(f"**❌ The {directory_type.capitalize()} directory does not exist.**")
        await callback_query.answer()
        return

    file_names = os.listdir(download_dir)
    total_files = len(file_names)
    total_pages = (total_files + files_per_page - 1) // files_per_page

    if total_files == 0:
        await callback_query.message.edit_text(f"**❌ No files have been uploaded yet in {directory_type.capitalize()} directory. Use /feed to start sending files.**")
        await callback_query.answer()
        return

    start_index = (page - 1) * files_per_page
    end_index = start_index + files_per_page
    page_files = file_names[start_index:end_index]

    file_list_message = "\n".join(page_files)
    reply_markup = []

    if page > 1:
        reply_markup.append(InlineKeyboardButton("✘Previous↯", callback_data=f"db_{directory_type}_{page-1}"))
    if page < total_pages:
        reply_markup.append(InlineKeyboardButton("✘Next↯", callback_data=f"db_{directory_type}_{page+1}"))

    await callback_query.message.edit_text(
        f"**📄 Uploaded Files in {directory_type.capitalize()} Directory (Page {page}/{total_pages}):**\n{file_list_message}",
        reply_markup=InlineKeyboardMarkup([reply_markup]) if reply_markup else None
    )
    await callback_query.answer()

@Client.on_message(filters.command("ping"))
async def ping_command_handler(client, message: Message):
    loading_message = await client.send_message(message.from_user.id, "**✘ Mr. ULP Bot Pinging...↯**")
    
    # Run speed test
    speed_result = await run_speedtest_task()

    # Format speed test results
    response = ""
    if "error" not in speed_result:
        response = (
            "**✘《 💥 SPEEDTEST RESULTS ↯ 》**\n"
            f"↯ **Upload Speed:** <code>{speed_convert(speed_result['upload'])}</code>\n"
            f"↯ **Download Speed:** <code>{speed_convert(speed_result['download'])}</code>\n"
            f"↯ **Ping:** <code>{speed_result['ping']:.2f} ms</code>\n"
            f"↯ **Timestamp:** <code>{speed_result['timestamp']}</code>\n"
            f"↯ **Data Sent:** <code>{get_readable_file_size(int(speed_result['bytes_sent']))}</code>\n"
            f"↯ **Data Received:** <code>{get_readable_file_size(int(speed_result['bytes_received']))}</code>\n"
            "**✘《 🌐 SERVER INFO ↯ 》**\n"
            f"↯ **Name:** <code>{speed_result['server']['name']}</code>\n"
            f"↯ **Country:** <code>{speed_result['server']['country']}, {speed_result['server']['cc']}</code>\n"
            f"↯ **Sponsor:** <code>{speed_result['server']['sponsor']}</code>\n"
            f"↯ **Latency:** <code>{speed_result['server']['latency']:.2f} ms</code>\n"
            f"↯ **Latitude:** <code>{speed_result['server']['lat']}</code>\n"
            f"↯ **Longitude:** <code>{speed_result['server']['lon']}</code>\n"
            "**✘《 👾 CLIENT INFO ↯ 》**\n"
            f"↯ **IP Address:** <code>{speed_result['client']['ip']}</code>\n"
            f"↯ **Latitude:** <code>{speed_result['client']['lat']}</code>\n"
            f"↯ **Longitude:** <code>{speed_result['client']['lon']}</code>\n"
            f"↯ **Country:** <code>{speed_result['client']['country']}</code>\n"
            f"↯ **ISP:** <code>{speed_result['client']['isp']}</code>\n"
            f"↯ **ISP Rating:** <code>{speed_result['client'].get('isprating', 'N/A')}</code>\n"
        )
    else:
        response = f"**✘ Speed Test Failed: {speed_result['error']} ↯**\n"

    # Add Update News button
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Update News", url="https://t.me/TheSmartDev")]
    ])

    # Edit the loading message with the final response
    await loading_message.edit_text(response, reply_markup=reply_markup)