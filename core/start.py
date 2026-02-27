import asyncio
import re

from telethon import events

import config
from bot import ItsMrULPBot
from helpers import LOGGER, SmartButtons, edit_message, send_message

prefixes = "".join(re.escape(p) for p in config.COMMAND_PREFIXES)
start_pattern = re.compile(rf"^[{prefixes}]start(?:\s+.+)?$", re.IGNORECASE)


def build_start_markup():
    sb = SmartButtons()
    sb.button("⚙ Main Menu", callback_data="main_menu", position="header")
    sb.button("ℹ️ About Me", callback_data="about")
    sb.button("📄 Policy & Terms", callback_data="policy")
    return sb.build_menu(b_cols=2, h_cols=1)


@ItsMrULPBot.on(events.NewMessage(pattern=start_pattern))
async def start_handler(event):
    sender = await event.get_sender()
    first_name = sender.first_name or ""
    last_name = sender.last_name or ""
    name = f"{first_name} {last_name}".strip() or "User"
    LOGGER.info(f"Start command | User: {name} ({sender.id})")

    msg = await send_message(event.chat_id, "**Starting ItsMrULPBot ⚙️....**")
    if not msg:
        return
    await asyncio.sleep(0.2)
    await edit_message(event.chat_id, msg.id, "**Generating Session Keys...**")
    await asyncio.sleep(0.2)

    text = (
        f"**Hi** {name} **Welcome To This Bot!**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"**ItsMrULPBot ⚙️** is your ultimate ULP toolkit on Telegram — process files & more with ease!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Don't forget to [join](https://{config.UPDATE_CHANNEL_URL}) for updates!"
    )

    await edit_message(
        event.chat_id, msg.id, text, link_preview=False, buttons=build_start_markup()
    )
