from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from databases import Databases

class Logs:
    """
    Manages logging operations and session data storage in MongoDB.

    This class is implemented as a singleton to ensure only one instance exists.
    It provides methods to ensure collection existence and upsert session data
    into a MongoDB database.

    Attributes:
        db (Databases): An instance of the Databases class for database operations.
    """

    _instance = None

    def __new__(cls, db : 'Databases'=None):
        if cls._instance is None:
            cls._instance = super(Logs, cls).__new__(cls)
            cls._instance.__initialized = False
        return cls._instance

    def __init__(self):
        if not self.__initialized:
            self.__initialized = True

    async def ensure_collection_exists(self, db: 'Databases', collection_name: str) -> None:
        collections = await db.list_collection_names()
        if collection_name not in collections:
            await db.create_collection(collection_name)

    async def upsert_session_data(self, db: 'Databases', collection_name: str, session_id: int, origin: str, question: str, answer: str) -> None:
        await self.ensure_collection_exists(db=db, collection_name=collection_name)
        collection = db[collection_name]
        
        # Try to find the existing document
        existing_doc = await collection.find_one({"session": session_id})
        
        if existing_doc:
            # If the document exists, update it
            await collection.update_one(
                {"session": session_id},
                {
                    "$push": {
                        "origins": {"$each": [origin]},
                        "questions": {"$each": [question]},
                        "answers": {"$each": [answer]}
                    }
                }
            )
        else:
            # If the document doesn't exist, insert a new one
            new_doc = {
                "session": session_id,
                "origins": [origin],
                "questions": [question],
                "answers": [answer]
            }
            await collection.insert_one(new_doc)