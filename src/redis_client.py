# src/redis_client.py
import redis.asyncio as redis
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.redis = None
        self._connected = False

    @property
    def is_connected(self):
        """Check if Redis is connected"""
        return self._connected

    async def connect(self):
        """Connect to Redis using environment variables"""
        try:
            # Get Redis configuration from environment variables
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            await self.redis.ping()
            self._connected = True
            logger.info(f"✅ Connected to Redis successfully at {redis_host}:{redis_port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("✅ Redis disconnected")

    async def is_processed(self, request_id: str) -> bool:
        """Check if request was already processed"""
        if not self._connected or not self.redis:
            logger.warning("📝 Redis not connected - skipping idempotency check")
            return False
            
        try:
            exists = await self.redis.exists(f"processed:{request_id}")
            return bool(exists)
        except Exception as e:
            logger.error(f"❌ Redis error in is_processed: {e}")
            return False

    async def mark_as_processed(self, request_id: str, ttl: int = 86400) -> bool:
        """Mark request as processed with TTL"""
        if not self._connected or not self.redis:
            logger.warning("📝 Redis not connected - skipping mark as processed")
            return False
            
        try:
            await self.redis.setex(f"processed:{request_id}", ttl, "true")
            logger.debug(f"📝 Marked request as processed: {request_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Redis error in mark_as_processed: {e}")
            return False


# Global instance
redis_client = RedisClient()