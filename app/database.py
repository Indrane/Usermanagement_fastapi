from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

# MongoDB connection string (from environment variable)
MONGO_CONNECTION_STRING = "mongodb+srv://indraneelshinde002:brightinfonet@cluster0.sgilo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGO_CONNECTION_STRING, server_api=ServerApi('1'))

# Test the connection
async def ping_server():
    try:
        await client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

# Database and collections
db = client["brightinfonet"]
users_collection = db["users"]
order_collection = db["orders"]