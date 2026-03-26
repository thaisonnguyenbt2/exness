import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseSchema:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/trading")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client.get_database()
        
    async def get_recent_candles(self, symbol: str, timeframe: str, limit: int = 100):
        try:
            cursor = self.db.candles.find(
                {"symbol": symbol, "timeframe": timeframe}
            ).sort("timestamp", -1).limit(limit)
            
            candles = await cursor.to_list(length=limit)
            # Reverse to temporal order (oldest first)
            return candles[::-1]
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return []

    async def insert_tick(self, symbol: str, price: float, volume: float, timestamp: int):
        try:
            await self.db.ticks.insert_one({
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "timestamp": timestamp,
                "created_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error inserting tick: {e}")

    async def insert_candle(self, symbol: str, timeframe: str, candle_data: dict):
        try:
            doc = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": candle_data["timestamp"],
                "created_at": datetime.utcnow()
            }
            doc.update(candle_data)
            await self.db.candles.insert_one(doc)
        except Exception as e:
            logger.error(f"Error inserting candle: {e}")

    async def init_indexes(self):
        """Create initial indexes for performance (normally run once)."""
        import pymongo
        try:
            await self.db.ticks.create_index([("timestamp", pymongo.DESCENDING), ("symbol", pymongo.ASCENDING)])
            await self.db.ticks.create_index("created_at", expireAfterSeconds=604800) # 7 days
            
            await self.db.candles.create_index([("timestamp", pymongo.DESCENDING), ("timeframe", pymongo.ASCENDING), ("symbol", pymongo.ASCENDING)])
            await self.db.candles.create_index("created_at", expireAfterSeconds=7776000) # 90 days
            logger.info("MongoDB indexes initialized")
        except Exception as e:
            logger.error(f"Error initializing indexes: {e}")

    async def close(self):
        self.client.close()
        logger.info("MongoDB connection closed")
