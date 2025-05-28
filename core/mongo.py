from pymongo import MongoClient
from utils import LOGGER
from config import MONGO_URL

# Initialize MongoDB Client
LOGGER.info("Creating MONGO_CLIENT From MONGO_URL")
try:
    MONGO_CLIENT = MongoClient(MONGO_URL)
    LOGGER.info("MONGO_CLIENT Successfully Created!")
except Exception as e:
    LOGGER.error(f"Failed to create MONGO_CLIENT: {e}")
    raise

# Access the database and collections
db = MONGO_CLIENT["ItsSmartTool"]  # Replace with your desired database name
user_activity_collection = db["user_credits"]  # Replace with your desired collection name