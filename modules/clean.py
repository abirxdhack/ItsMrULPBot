import asyncio
import re
import shutil
from pathlib import Path
from typing import Dict, List

from telethon import Button, events

import config
from bot import ItsMrULPBot
from helpers import LOGGER, SmartButtons, edit_message, new_task, send_message

prefixes = "".join(re.escape(p) for p in config.COMMAND_PREFIXES)
_clean_pattern = re.compile(rf"^[{prefixes}]clean$", re.IGNORECASE)
_files_pattern = re.compile(rf"^[{prefixes}]files$", re.IGNORECASE)

_AUTHORIZED_IDS = {config.OWNER_ID, config.ADMIN_ID}
_PAGE_SIZE = 5
_sessions: Dict[int, Dict] = {}


def _auth(uid: int) -> bool:
    return uid in _AUTHORIZED_IDS


def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _dl_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "downloads"


def _data_files() -> List[Path]:
    d = _data_dir()
    return sorted(f for f in d.glob("*.txt") if f.is_file()) if d.exists() else []


def _dl_files() -> List[Path]:
    d = _dl_dir()
    return sorted(f for f in d.iterdir() if f.is_file()) if d.exists() else []


def _clean_name(name: str) -> str:
    stem = re.sub(r"[_\-]+", " ", Path(name).stem)
    return stem.strip().title()


def _fmt(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 ** 2:
        return f"{b / 1024:.2f} KB"
    if b < 1024 ** 3:
        return f"{b / (1024 ** 2):.2f} MB"
    return f"{b / (1024 ** 3):.2f} GB"


def _dir_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.iterdir() if f.is_file()) if p.exists() else 0


def _disk() -> str:
    try:
        total, used, _ = shutil.disk_usage("/")
        return f"{_fmt(used)} of {_fmt(total)}"
    except Exception:
        return "N/A"


def _page_text(files: List[Path], page: int) -> str:
    start = page * _PAGE_SIZE
    lines = [
        "**🔍 Showing Bot's Database Info 📋**",
        "**━━━━━━━━━━━━━━━━**",
    ]
    for i, f in enumerate(files[start: start + _PAGE_SIZE], start=start + 1):
        lines.append(f"**{i}. {_clean_name(f.name)}**")
    lines.append("**━━━━━━━━━━━━━━━━**")
    lines.append("**👁 Navigate These Buttons For Next ✅**")
    return "\n".join(lines)


def _nav_buttons(page: int, total: int, cid: int):
    row = []
    if page > 0:
        row.append(Button.inline("◀️ Previous", data=f"dbpg:prev:{cid}:{page}".encode()))
    if page < total - 1:
        row.append(Button.inline("Next ➡️", data=f"dbpg:next:{cid}:{page}".encode()))
    return [row] if row else None


def _clean_buttons():
    return [
        [Button.inline("📁 Clean Up DB", data=b"dbclean:data"),
         Button.inline("📥 Clean Up Dump", data=b"dbclean:downloads")]
    ]


@ItsMrULPBot.on(events.NewMessage(pattern=_files_pattern))
@new_task
async def files_handler(event, bot):
    sender = await event.get_sender()
    if not _auth(sender.id):
        return
    chat_id = event.chat_id
    loop = asyncio.get_running_loop()
    files = await loop.run_in_executor(None, _data_files)
    if not files:
        await send_message(chat_id, "**❌ No Database Files Found**")
        return
    total = max(1, (len(files) + _PAGE_SIZE - 1) // _PAGE_SIZE)
    _sessions[chat_id] = {"files": files, "total": total}
    msg = await send_message(chat_id, "**🔍 Loading Database Info...**")
    if not msg:
        return
    btns = _nav_buttons(0, total, chat_id)
    await ItsMrULPBot.edit_message(chat_id, msg.id, _page_text(files, 0), parse_mode="markdown", buttons=btns)


@ItsMrULPBot.on(events.CallbackQuery(data=re.compile(rb"^dbpg:")))
async def files_nav_cb(event):
    sender = await event.get_sender()
    if not _auth(sender.id):
        await event.answer("❌ Not Authorized", alert=True)
        return
    raw = event.data.decode()
    parts = raw.split(":")
    direction, chat_id, cur = parts[1], int(parts[2]), int(parts[3])
    session = _sessions.get(chat_id)
    if not session:
        await event.answer("Session expired. Run /files again.", alert=True)
        return
    files, total = session["files"], session["total"]
    page = cur + 1 if direction == "next" else cur - 1
    page = max(0, min(page, total - 1))
    btns = _nav_buttons(page, total, chat_id)
    msg_id = event.query.msg_id
    await ItsMrULPBot.edit_message(chat_id, msg_id, _page_text(files, page), parse_mode="markdown", buttons=btns)


@ItsMrULPBot.on(events.NewMessage(pattern=_clean_pattern))
@new_task
async def clean_handler(event, bot):
    sender = await event.get_sender()
    if not _auth(sender.id):
        return
    chat_id = event.chat_id
    loop = asyncio.get_running_loop()

    msg = await send_message(chat_id, "**Checking System Storage...**")
    if not msg:
        return

    df = await loop.run_in_executor(None, _data_files)
    dl = await loop.run_in_executor(None, _dl_files)
    db_sz = await loop.run_in_executor(None, _dir_size, _data_dir())
    disk = await loop.run_in_executor(None, _disk)

    text = (
        "**🔍 Showing Bot's Database Info 📋**\n"
        "**━━━━━━━━━━━━━━━━**\n"
        f"**Total Files** : `{len(df)}`\n"
        f"**Total DB Size** : `{_fmt(db_sz)}`\n"
        f"**Total Generated DB** : `{len(dl)}`\n"
        f"**Storage Used** : `{disk}`\n"
        "**━━━━━━━━━━━━━━━━**\n"
        "**👁 Navigate These Buttons For Next ✅**"
    )
    await ItsMrULPBot.edit_message(chat_id, msg.id, text, parse_mode="markdown", buttons=_clean_buttons())


@ItsMrULPBot.on(events.CallbackQuery(data=re.compile(rb"^dbclean:")))
async def clean_action_cb(event):
    sender = await event.get_sender()
    if not _auth(sender.id):
        await event.answer("❌ Not Authorized", alert=True)
        return
    target = event.data.decode().split(":", 1)[1]
    loop = asyncio.get_running_loop()
    msg_id = event.query.msg_id
    chat_id = event.chat_id

    if target == "data":
        await ItsMrULPBot.edit_message(chat_id, msg_id, "**Cleaning Up Database Files...📄**", parse_mode="markdown", buttons=None)
        files = await loop.run_in_executor(None, _data_files)
        if not files:
            await ItsMrULPBot.edit_message(chat_id, msg_id, "**Sorry Files To Clean Not Found ❌**", parse_mode="markdown", buttons=None)
            return
        def _del():
            failed = 0
            for f in files:
                try:
                    f.unlink()
                    LOGGER.info(f"Cleaning Download: {f.name}")
                except Exception as e:
                    LOGGER.error(f"Failed to delete {f.name}: {e}")
                    failed += 1
            return failed
        failed = await loop.run_in_executor(None, _del)
        result = "**Successfully Cleaned Up Database...📥**" if failed == 0 else "**Sorry Files To Clean Not Found ❌**"
        await ItsMrULPBot.edit_message(chat_id, msg_id, result, parse_mode="markdown", buttons=None)

    elif target == "downloads":
        await ItsMrULPBot.edit_message(chat_id, msg_id, "**Cleaning Up Processed Files...📥**", parse_mode="markdown", buttons=None)
        files = await loop.run_in_executor(None, _dl_files)
        if not files:
            await ItsMrULPBot.edit_message(chat_id, msg_id, "**Sorry Files To Clean Not Found ❌**", parse_mode="markdown", buttons=None)
            return
        def _del():
            failed = 0
            for f in files:
                try:
                    f.unlink()
                    LOGGER.info(f"Cleaning Download: {f.name}")
                except Exception as e:
                    LOGGER.error(f"Failed to delete {f.name}: {e}")
                    failed += 1
            return failed
        failed = await loop.run_in_executor(None, _del)
        result = "**Successfully Cleaned Up Files...📄**" if failed == 0 else "**❌ Failed To Clean Up The Files**"
        await ItsMrULPBot.edit_message(chat_id, msg_id, result, parse_mode="markdown", buttons=None)