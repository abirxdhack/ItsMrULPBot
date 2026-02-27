import asyncio
import functools
import os
from helpers.logger import LOGGER


def new_task(func):
    @functools.wraps(func)
    async def wrapper(event, *args, **kwargs):
        try:
            bot = kwargs.pop("bot", None)
            task = asyncio.create_task(func(event, bot, **kwargs))
            task.add_done_callback(
                lambda t: LOGGER.error(f"{func.__name__} failed: {t.exception()}")
                if not t.cancelled() and t.exception()
                else None
            )
        except Exception as e:
            LOGGER.error(f"new_task error in {func.__name__}: {e}")
    return wrapper


def clean_download(*files):
    for file in files:
        try:
            if file and os.path.exists(file):
                parts = file.replace("\\", "/").split("/")
                dl_idx = next((i for i, p in enumerate(parts) if p == "downloads"), None)
                label = "/".join(parts[dl_idx:]) if dl_idx is not None else parts[-1]
                os.remove(file)
                LOGGER.info(f"Cleaning Download: {label}")
        except Exception as e:
            LOGGER.error(f"clean_download error for {file}: {e}")
