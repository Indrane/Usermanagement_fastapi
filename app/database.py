from pymongo import MongoClient
from pymongo.server_api import ServerApi

# MongoDB connection string (from environment variable)
MONGO_CONNECTION_STRING = "mongodb+srv://vittavridhi_dev:E2Aa9nKnGaxVqEk9@vittavridhi.fldh0nd.mongodb.net/?retryWrites=true&w=majority&appName=vittavridhi"

# Initialize MongoDB client
client = MongoClient(MONGO_CONNECTION_STRING, server_api=ServerApi('1'))

# Test the connection
def ping_server():
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

# Database and collections
db = client["brightinfonet"]
users_collection = db["users"]
order_collection = db["orders"]

# Test the connection
# ping_server()
