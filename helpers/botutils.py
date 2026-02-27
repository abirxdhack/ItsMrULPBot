from typing import Optional, Union

from telethon.errors import (
    MessageNotModifiedError,
    MessageIdInvalidError,
    ChatWriteForbiddenError,
    FloodWaitError,
    UserIsBlockedError,
)
from telethon.tl.types import Message

from bot import ItsMrULPBot
from helpers.logger import LOGGER


async def send_message(chat_id, text, parse_mode='markdown', buttons=None,
                       reply_to=None, link_preview=False, silent=None,
                       background=None, formatting_entities=None,
                       clear_draft=False, schedule=None, comment_to=None):
    try:
        return await ItsMrULPBot.send_message(
            entity=chat_id, message=text, parse_mode=parse_mode,
            buttons=buttons, reply_to=reply_to, link_preview=link_preview,
            silent=silent, background=background,
            formatting_entities=formatting_entities,
            clear_draft=clear_draft, schedule=schedule, comment_to=comment_to,
        )
    except FloodWaitError as e:
        LOGGER.warning(f"FloodWait {e.seconds}s on send_message to {chat_id}")
        return None
    except (ChatWriteForbiddenError, UserIsBlockedError) as e:
        LOGGER.warning(f"Cannot send to {chat_id}: {e}")
        return None
    except Exception as e:
        LOGGER.error(f"Failed to send message to {chat_id}: {e}")
        return None


async def edit_message(chat_id, message, text, parse_mode='markdown',
                       buttons=None, link_preview=False,
                       formatting_entities=None, file=None,
                       force_document=False, schedule=None):
    try:
        return await ItsMrULPBot.edit_message(
            entity=chat_id, message=message, text=text, parse_mode=parse_mode,
            buttons=buttons, link_preview=link_preview,
            formatting_entities=formatting_entities, file=file,
            force_document=force_document, schedule=schedule,
        )
    except MessageNotModifiedError:
        return None
    except MessageIdInvalidError as e:
        LOGGER.warning(f"Message ID invalid on edit in {chat_id}: {e}")
        return None
    except FloodWaitError as e:
        LOGGER.warning(f"FloodWait {e.seconds}s on edit_message in {chat_id}")
        return None
    except Exception as e:
        LOGGER.error(f"Failed to edit message in {chat_id}: {e}")
        return None


async def delete_messages(chat_id, message_ids, revoke=True):
    try:
        if isinstance(message_ids, int):
            message_ids = [message_ids]
        await ItsMrULPBot.delete_messages(entity=chat_id, message_ids=message_ids, revoke=revoke)
        return True
    except FloodWaitError as e:
        LOGGER.warning(f"FloodWait {e.seconds}s on delete_messages in {chat_id}")
        return False
    except Exception as e:
        LOGGER.error(f"Failed to delete messages {message_ids} in {chat_id}: {e}")
        return False


async def send_file(chat_id, file, caption=None, parse_mode='markdown',
                    buttons=None, thumb=None, attributes=None, reply_to=None,
                    silent=None, background=None, force_document=False,
                    supports_streaming=False, voice_note=False, video_note=False,
                    formatting_entities=None, progress_callback=None,
                    clear_draft=False, schedule=None, comment_to=None, ttl=None):
    try:
        return await ItsMrULPBot.send_file(
            entity=chat_id, file=file, caption=caption, parse_mode=parse_mode,
            buttons=buttons, thumb=thumb, attributes=attributes, reply_to=reply_to,
            silent=silent, background=background, force_document=force_document,
            supports_streaming=supports_streaming, voice_note=voice_note,
            video_note=video_note, formatting_entities=formatting_entities,
            progress_callback=progress_callback, clear_draft=clear_draft,
            schedule=schedule, comment_to=comment_to, ttl=ttl,
        )
    except FloodWaitError as e:
        LOGGER.warning(f"FloodWait {e.seconds}s on send_file to {chat_id}")
        return None
    except (ChatWriteForbiddenError, UserIsBlockedError) as e:
        LOGGER.warning(f"Cannot send file to {chat_id}: {e}")
        return None
    except Exception as e:
        LOGGER.error(f"Failed to send file to {chat_id}: {e}")
        return None


async def get_messages(chat_id, message_ids):
    try:
        return await ItsMrULPBot.get_messages(entity=chat_id, ids=message_ids)
    except Exception as e:
        LOGGER.error(f"Failed to get messages {message_ids} in {chat_id}: {e}")
        return None


async def forward_messages(to_chat, messages, from_chat, silent=None,
                           drop_author=False, schedule=None):
    try:
        if isinstance(messages, int):
            messages = [messages]
        return await ItsMrULPBot.forward_messages(
            entity=to_chat, messages=messages, from_peer=from_chat,
            silent=silent, drop_author=drop_author, schedule=schedule,
        )
    except FloodWaitError as e:
        LOGGER.warning(f"FloodWait {e.seconds}s on forward_messages to {to_chat}")
        return None
    except Exception as e:
        LOGGER.error(f"Failed to forward messages to {to_chat}: {e}")
        return None


def get_args(message):
    text = message.text if hasattr(message, 'text') else str(message)
    if not text:
        return []
    parts = text.split(None, 1)
    if len(parts) < 2:
        return []
    args_str = parts[1].strip()
    if not args_str:
        return []
    result = []
    current = ""
    in_quotes = False
    quote_char = None
    i = 0
    while i < len(args_str):
        char = args_str[i]
        if char in ('"', "'") and (i == 0 or args_str[i - 1] != '\\'):
            if in_quotes and char == quote_char:
                in_quotes = False
                quote_char = None
                if current:
                    result.append(current)
                    current = ""
            else:
                in_quotes = True
                quote_char = char
        elif char == ' ' and not in_quotes:
            if current:
                result.append(current)
                current = ""
        else:
            current += char
        i += 1
    if current:
        result.append(current)
    return result


def get_args_str(message):
    text = message.text if hasattr(message, 'text') else str(message)
    if not text:
        return ""
    parts = text.split(None, 1)
    return parts[1].strip() if len(parts) >= 2 else ""


def mention_user(name, user_id):
    return f"[{name}](tg://user?id={user_id})"
