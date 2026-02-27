import asyncio
import importlib.util
import sys
from pathlib import Path

import uvloop

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

from helpers.logger import LOGGER
from bot import ItsMrULPBot, start_bot

HANDLER_DIRS = [
    Path(__file__).parent / "core",
    Path(__file__).parent / "modules",
]


def load_handlers():
    for directory in HANDLER_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.py")):
            if path.name == "__init__.py":
                continue
            module_name = f"{directory.name}.{path.stem}"
            if module_name in sys.modules:
                continue
            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
            except Exception as e:
                LOGGER.error(f"Failed to load {module_name}: {e}")


async def run_bot():
    await start_bot()
    load_handlers()
    me = await ItsMrULPBot.get_me()
    LOGGER.info(f"Bot Successfully Started! 💥")
    await ItsMrULPBot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        LOGGER.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        LOGGER.error(f"Fatal error: {e}")
        sys.exit(1)
