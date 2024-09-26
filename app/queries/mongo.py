import asyncio
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection

class Mongo:
    """
    A class for performing MongoDB operations, particularly vector searches across collections.

    This class provides methods for searching single collections and performing multi-collection
    vector searches asynchronously.
    """

    async def search_single_collection(
        self, 
        db: AsyncIOMotorDatabase, 
        query_vector: List[float], 
        collection_name: str, 
        k: int
    ) -> List[Dict[str, Any]]:
        """
        Perform a vector search on a single collection.

        Args:
            db (AsyncIOMotorDatabase): The MongoDB database instance.
            query_vector (List[float]): The query vector for the search.
            collection_name (str): The name of the collection to search.
            k (int): The number of results to return.

        Returns:
            List[Dict[str, Any]]: A list of search results.
        """
        pipeline = [
            {
                "$search": {
                    "cosmosSearch": {
                        "vector": query_vector,
                        "path": "embedding",
                        "k": k*5,
                    },
                    "returnStoredSource": True
                }
            },
            {
                "$project": {
                    "content": 1,
                    "chunk": 1,
                    "origin": 1,
                    "vertex": 1,
                    "score": {"$meta": "searchScore"},
                    "collection": {"$literal": collection_name}
                }
            },
            {
                "$group": {
                    "_id": "$content",
                    "doc": {"$first": "$$ROOT"},
                    "maxScore": {"$max": "$score"}
                }
            },
            {
                "$replaceRoot": {"newRoot": "$doc"}
            },
            {
                "$sort": {"score": -1}
            }
        ]
        collection: AsyncIOMotorCollection = db[collection_name]
        cursor = collection.aggregate(pipeline)
        return await cursor.to_list(length=None)

    async def multi_collection_vector_search(
        self, 
        db: AsyncIOMotorDatabase, 
        query_vector: List[float], 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform a vector search across multiple collections asynchronously.

        Args:
            db (AsyncIOMotorDatabase): The MongoDB database instance.
            query_vector (List[float]): The query vector for the search.
            k (int, optional): The number of results to return. Defaults to 5.

        Returns:
            List[Dict[str, Any]]: A list of search results from all collections, sorted by score.
        """
        collection_names = await db.get_collection_names()
        tasks = [self.search_single_collection(db.db, query_vector, name, k) for name in collection_names]
        results = await asyncio.gather(*tasks)
        
        all_results = [item for sublist in results for item in sublist]
        all_results.sort(key=lambda x: x['score'], reverse=True)

        return all_results[:k]