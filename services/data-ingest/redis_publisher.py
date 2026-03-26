import os
import json
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class RedisPublisher:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.connected = False

    async def connect(self):
        try:
            await self.redis.ping()
            self.connected = True
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.connected = False

    async def publish_price_update(self, symbol: str, price: float, timestamp: int):
        if not self.connected:
            return
        
        channel = "price:updates"
        message = {
            "symbol": symbol,
            "price": price,
            "timestamp": timestamp
        }
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")

    async def publish_candle(self, symbol: str, timeframe: str, candle_data: dict):
        if not self.connected:
            return
            
        channel = f"candles:{timeframe}"
        message = {
            "symbol": symbol,
            "timeframe": timeframe,
            "candle": candle_data
        }
        try:
            await self.redis.publish(channel, json.dumps(message))
        except Exception as e:
            logger.error(f"Error publishing to {channel}: {e}")

    async def close(self):
        await self.redis.close()
        self.connected = False
        logger.info("Redis connection closed")
