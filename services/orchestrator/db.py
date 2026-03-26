import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

class Database:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/trading")
        self.client = AsyncIOMotorClient(self.uri)
        self.db = self.client.trading

    async def get_system_config(self):
        config = await self.db.system_config.find_one({"_id": "global_config"})
        if not config:
            # Default config
            config = {"paper_trading_enabled": True, "risk_per_trade_percent": 1.0}
            await self.db.system_config.insert_one({"_id": "global_config", **config})
        return config

    async def record_trade(self, trade_data: dict):
        trade_data['created_at'] = datetime.now(timezone.utc)
        return await self.db.paper_trades.insert_one(trade_data)

    async def get_open_trades(self, symbol: str):
        cursor = self.db.paper_trades.find({"symbol": symbol, "status": "OPEN"})
        return await cursor.to_list(length=100)

    async def close_trade(self, trade_id, exit_price, pnl):
        await self.db.paper_trades.update_one(
            {"_id": trade_id},
            {"$set": {
                "status": "CLOSED",
                "exit_price": exit_price,
                "pnl": pnl,
                "closed_at": datetime.now(timezone.utc)
            }}
        )

db = Database()
