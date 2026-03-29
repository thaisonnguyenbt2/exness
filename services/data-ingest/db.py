import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class DatabaseSchema:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017/trading")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client.get_database()
        
    async def setup_indexes(self):
        try:
            from pymongo import ASCENDING, DESCENDING
            await self.db.candles.create_index(
                [("symbol", ASCENDING), ("timeframe", ASCENDING), ("timestamp", DESCENDING)],
                unique=True
            )
            logger.info("MongoDB indexing uniquely compiled natively for candles collection")
        except Exception as e:
            logger.error(f"Error creating indexes natively: {e}")

    async def save_candle(self, symbol: str, timeframe: str, active: dict):
        try:
            payload = active.copy()
            payload["symbol"] = symbol
            payload["timeframe"] = timeframe
            
            await self.db.candles.update_one(
                {"symbol": symbol, "timeframe": timeframe, "timestamp": active["timestamp"]},
                {"$set": payload},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving atomic candle recursively to MongoDB: {e}")

    async def save_candles_bulk(self, symbol: str, timeframe: str, candles: list):
        if not candles: return
        try:
            from pymongo import UpdateOne
            operations = []
            for c in candles:
                payload = c.copy()
                payload["symbol"] = symbol
                payload["timeframe"] = timeframe
                operations.append(
                    UpdateOne(
                        {"symbol": symbol, "timeframe": timeframe, "timestamp": c["timestamp"]},
                        {"$set": payload},
                        upsert=True
                    )
                )
            await self.db.candles.bulk_write(operations, ordered=False)
            logger.info(f"Dynamically bulk-written {len(candles)} historical {timeframe} candles strictly into MongoDB!")
        except Exception as e:
            logger.error(f"Error bulk violently saving candles to MongoDB arrays: {e}")

    async def close(self):
        self.client.close()
        logger.info("MongoDB persistent connection cleanly closed")
