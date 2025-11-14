import redis.asyncio as redis
import logging
from typing import Optional
import os
import asyncio
from urllib.parse import urlparse

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
        """Connect to Redis using a REDIS_URL environment variable"""
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

            # Upstash requires ssl_certfile=None to use default system certs
            # and longer timeouts for network stability
            connect_kwargs = {
                "decode_responses": True,
                "socket_connect_timeout": 15,
                "socket_timeout": 15,
                "retry_on_timeout": True,
            }

            # For Upstash (rediss://) add SSL settings
            if redis_url.startswith("rediss://"):
                connect_kwargs["ssl_certfile"] = None  # Use system CA bundle
                connect_kwargs["ssl"] = True
                connect_kwargs["ssl_check_hostname"] = True

            # Create Redis client directly from URL
            self.redis = redis.from_url(redis_url, **connect_kwargs)

            # Test connection with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.redis.ping()
                    self._connected = True
                    logger.info(f"✅ Connected to Redis successfully: {redis_url}")
                    return True
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"⚠️ Redis connection attempt {attempt + 1} failed, retrying... Error: {e}"
                        )
                        await asyncio.sleep(2)
                    else:
                        raise

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
