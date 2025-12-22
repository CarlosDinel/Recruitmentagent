"""MongoDB client configuration and connection management."""

import os
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()


class MongoDBClient:
    """MongoDB client singleton for connection management."""
    
    _instance: Optional['MongoDBClient'] = None
    _client: Optional[MongoClient] = None
    _database: Optional[Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish MongoDB connection."""
        username = os.getenv('MONGO_USERNAME')
        password = os.getenv('MONGO_PASSWORD')
        host = os.getenv('MONGO_HOST')
        database = os.getenv('MONGO_DATABASE', 'recruitment_db')
        
        if not all([username, password, host]):
            raise ValueError(
                "MongoDB configuration incomplete. "
                "Required: MONGO_USERNAME, MONGO_PASSWORD, MONGO_HOST"
            )
        
        uri = f"mongodb+srv://{username}:{password}@{host}/{database}?retryWrites=true&w=majority"
        
        self._client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        self._database = self._client[database]
        
        # Test connection
        self._client.server_info()
    
    @property
    def client(self) -> MongoClient:
        """Get MongoDB client."""
        if self._client is None:
            self._connect()
        return self._client
    
    @property
    def database(self) -> Database:
        """Get database instance."""
        if self._database is None:
            self._connect()
        return self._database
    
    def close(self):
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
    
    def get_collection(self, collection_name: str):
        """Get a collection from the database."""
        return self.database[collection_name]

