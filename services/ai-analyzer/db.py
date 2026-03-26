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
            return candles[::-1] # return chronological
        except Exception as e:
            logger.error(f"Error fetching candles: {e}")
            return []

    async def save_signal(self, signal_data: dict):
        try:
            doc = {
                "created_at": datetime.utcnow(),
                "status": "pending_notification"
            }
            doc.update(signal_data)
            result = await self.db.signals.insert_one(doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            return None

    async def close(self):
        self.client.close()
        logger.info("MongoDB connection closed")
