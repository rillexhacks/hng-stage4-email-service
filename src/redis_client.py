# src/redis_client.py
import redis.asyncio as redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis = None
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("✅ Connected to Redis successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("✅ Redis disconnected")
    
    async def is_processed(self, request_id: str) -> bool:
        """Check if request was already processed"""
        if not self.redis:
            return False
        return await self.redis.exists(f"processed:{request_id}")
    
    async def mark_as_processed(self, request_id: str, ttl: int = 86400) -> bool:
        """Mark request as processed with TTL"""
        if not self.redis:
            return False
        await self.redis.setex(f"processed:{request_id}", ttl, "true")
        logger.debug(f"📝 Marked request as processed: {request_id}")
        return True

# Global instance
redis_client = RedisClient()