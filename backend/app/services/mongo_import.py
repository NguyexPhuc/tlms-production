"""
MongoDB Service - Connect to S4H MongoDB for user import
Security: Connection string is read from environment variable only
"""
import logging
from typing import List, Optional, AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from app.core.config import get_settings
from app.schemas.mongo_import import MongoDBUser

logger = logging.getLogger(__name__)
settings = get_settings()


class MongoDBService:
    """
    Service for connecting to MongoDB and reading user data
    
    Security Notes:
    - Connection string is ONLY read from environment variable
    - NEVER log connection string or credentials
    - Connection is closed after each operation
    """

    def __init__(self):
        self._client: Optional[AsyncIOMotorClient] = None
        self._collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self) -> bool:
        """
        Connect to MongoDB using connection string from environment
        
        Returns:
            True if connection successful, False otherwise
        """
        if not settings.MONGODB_CONNECTION_STRING:
            logger.error("MongoDB connection string not configured")
            return False

        try:
            # Create client with connection string
            self._client = AsyncIOMotorClient(
                settings.MONGODB_CONNECTION_STRING,
                serverSelectionTimeoutMS=10000,  # 10 seconds timeout
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            
            # Test connection by pinging
            await self._client.admin.command('ping')
            
            # Get collection
            db = self._client[settings.MONGODB_DATABASE]
            self._collection = db[settings.MONGODB_USERS_COLLECTION]
            
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DATABASE}.{settings.MONGODB_USERS_COLLECTION}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            await self.disconnect()
            return False

    async def disconnect(self):
        """Close MongoDB connection"""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._collection = None
            logger.info("MongoDB connection closed")

    async def get_users_count(self) -> int:
        """Get total number of users in MongoDB"""
        if self._collection is None:
            return 0

        try:
            count = await self._collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting users: {str(e)}")
            return 0

    async def stream_users(self, batch_size: int = 100) -> AsyncGenerator[List[MongoDBUser], None]:
        """
        Stream users from MongoDB in batches

        Args:
            batch_size: Number of users per batch

        Yields:
            List of MongoDBUser objects
        """
        if self._collection is None:
            return

        try:
            cursor = self._collection.find({}).batch_size(batch_size)
            
            batch = []
            async for doc in cursor:
                try:
                    # Map MongoDB document to schema
                    # Only extract needed fields
                    user = MongoDBUser(
                        userId=doc.get("userId", ""),
                        email=doc.get("email", ""),
                        firstName=doc.get("firstName"),
                        lastName=doc.get("lastName"),
                        studentId=doc.get("studentId"),
                        phone=doc.get("phone"),
                        zaloUid=doc.get("zaloUid"),
                        roles=doc.get("roles"),
                        createdAt=doc.get("createdAt"),
                        updatedAt=doc.get("updatedAt")
                    )
                    batch.append(user)
                    
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
                        
                except Exception as e:
                    logger.warning(f"Error parsing user document: {str(e)}")
                    continue
            
            # Yield remaining batch
            if batch:
                yield batch
                
        except Exception as e:
            logger.error(f"Error streaming users: {str(e)}")
            raise

    async def get_all_users(self) -> List[MongoDBUser]:
        """
        Get all users from MongoDB
        
        Returns:
            List of MongoDBUser objects
        """
        all_users = []
        async for batch in self.stream_users():
            all_users.extend(batch)
        return all_users


# Singleton instance
mongo_db_service = MongoDBService()
