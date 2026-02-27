import asyncio
import re
import time
from pathlib import Path

from telethon import events

import config
from bot import ItsMrULPBot
from helpers import (
    LOGGER,
    SmartButtons,
    clean_download,
    delete_messages,
    edit_message,
    new_task,
    progress_bar,
    send_file,
    send_message,
)
from helpers.botutils import get_args_str
from helpers.func import run_ulp_search, get_file_size_str, write_ulp_file

prefixes = "".join(re.escape(p) for p in config.COMMAND_PREFIXES)
ulp_pattern = re.compile(rf"^[{prefixes}]ulp(?:\s+.+)?$", re.IGNORECASE)


def build_channel_button():
    sb = SmartButtons()
    sb.button("Updates Channel 🇧🇩", url=f"https://{config.UPDATE_CHANNEL_URL}")
    return sb.build_menu(b_cols=1)


@ItsMrULPBot.on(events.NewMessage(pattern=ulp_pattern))
@new_task
async def ulp_handler(event, bot):
    keyword = get_args_str(event).strip()
    chat_id = event.chat_id

    if not keyword:
        await send_message(chat_id, "**❌ Please Provide Keyword After The Command**")
        return

    status_msg = await send_message(chat_id, "**Searching Whole Database For Keyword 🔍**")
    if not status_msg:
        return

    try:
        matched_lines, duplicates_removed, elapsed_ms = await run_ulp_search(keyword, __file__)
    except Exception as exc:
        LOGGER.error(f"ulp_handler error: {exc}")
        await edit_message(chat_id, status_msg.id, "**❌ Sorry Database Empty**")
        return

    if not matched_lines:
        await edit_message(chat_id, status_msg.id, "**❌ Sorry Database Empty**")
        return

    await edit_message(chat_id, status_msg.id, "**Found ☑️ Processing...**")

    try:
        file_path = await asyncio.get_running_loop().run_in_executor(
            None, write_ulp_file, keyword, matched_lines
        )
    except Exception as exc:
        LOGGER.error(f"ulp_handler write error: {exc}")
        await edit_message(chat_id, status_msg.id, "**❌ Failed To Write Output File**")
        return

    fname = Path(file_path).name
    fsize = get_file_size_str(file_path)
    last_upd = [time.time()]
    t_start = time.time()

    async def _on_progress(cur, tot):
        await progress_bar(cur, tot, status_msg, t_start, last_upd)

    await send_file(
        chat_id,
        file_path,
        caption=(
            f"**🔍 Showing Processed File's Info 📋**\n"
            f"**━━━━━━━━━━━━━━━━**\n"
            f"**File Name** : `{fname}`\n"
            f"**File Size** : `{fsize}`\n"
            f"**File Format** : `Text Based ULP`\n"
            f"**Matched Lines** : `{len(matched_lines)}`\n"
            f"**Duplicates Removed** : `{duplicates_removed}`\n"
            f"**Time Taken** : `{elapsed_ms}ms`\n"
            f"**━━━━━━━━━━━━━━━━**\n"
            f"**Thanks For Using Smart Service 📥**"
        ),
        force_document=True,
        buttons=build_channel_button(),
        progress_callback=_on_progress,
    )

    await delete_messages(chat_id, status_msg.id)
    clean_download(file_path)
