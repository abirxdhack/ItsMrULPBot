from app import app
from utils import LOGGER
from core import start_message
from core.mongo import MONGO_CLIENT 

if __name__ == "__main__":
    LOGGER.info("Bot Successfully Started! ")
    app.run()