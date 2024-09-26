import os
from typing import List, Dict, Any
from utils import Utils
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

class Database:
    """
    Manages MongoDB operations and collections for the application.

    Attributes:
        db (AsyncIOMotorDatabase): The MongoDB database instance.
    """

    def __init__(self, utils: Utils):
        # Configuration
        USER = utils.vault.get_secret(os.environ['MONGO_USERNAME'])
        PASSWORD = utils.vault.get_secret(os.environ['MONGO_PASSWORD'])
        HOSTNAME = utils.vault.get_secret(os.environ['MONGO_HOST'])
        DB_NAME = os.environ['MONGO_DB']
        CONNECTION_STRING = f"mongodb+srv://{USER}:{PASSWORD}@{HOSTNAME}/{DB_NAME}?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"

        # MongoDB client setup
        mongo_client = AsyncIOMotorClient(CONNECTION_STRING)
        self.db: AsyncIOMotorDatabase = mongo_client[DB_NAME]

    async def get_collection_names(self) -> List[str]:
        return await self.db.list_collection_names()

    async def insert_document(self, collection_name: str, document: Dict[str, Any]) -> None:
        collection = self.db[collection_name]
        await collection.insert_one(document)

    async def find_document(self, collection_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
        collection = self.db[collection_name]
        return await collection.find_one(query)

    async def update_document(self, collection_name: str, query: Dict[str, Any], update: Dict[str, Any]) -> None:
        collection = self.db[collection_name]
        await collection.update_one(query, {'$set': update})

    async def delete_document(self, collection_name: str, query: Dict[str, Any]) -> None:
        collection = self.db[collection_name]
        await collection.delete_one(query)

    async def get_all_documents(self, collection_name: str) -> List[Dict[str, Any]]:
        collection = self.db[collection_name]
        cursor = collection.find({})
        return await cursor.to_list(length=None)