# src/redis_client.py
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class MockRedisClient:
    """
    Mock Redis client for testing - stores data in memory
    """
    def __init__(self):
        self._storage = {}
        logger.info("✅ Mock Redis client initialized (in-memory storage)")
    
    async def connect(self):
        """Mock connection method"""
        logger.info("✅ Mock Redis connected")
        return True
    
    async def disconnect(self):
        """Mock disconnect method"""
        logger.info("✅ Mock Redis disconnected")
        return True
    
    async def is_processed(self, request_id: str) -> bool:
        """Check if request was already processed"""
        return request_id in self._storage
    
    async def mark_as_processed(self, request_id: str, ttl: int = 86400) -> bool:
        """Mark request as processed"""
        self._storage[request_id] = True
        logger.debug(f"📝 Marked request as processed: {request_id}")
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        return self._storage.get(key)
    
    async def set(self, key: str, value: str, ttl: int = 86400) -> bool:
        """Set value with TTL"""
        self._storage[key] = value
        return True

# Global mock instance
redis_client = MockRedisClient()