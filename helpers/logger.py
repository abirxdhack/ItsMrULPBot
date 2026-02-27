import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

for _name in (
    "telethon",
    "telethon.client",
    "telethon.network",
    "telethon.extensions",
    "telethon.sessions",
):
    logging.getLogger(_name).setLevel(logging.ERROR)

LOGGER = logging.getLogger(__name__)
