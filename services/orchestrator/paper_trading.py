import json
import asyncio
import redis.asyncio as redis
import os
from db import db

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL)

async def simulate_paper_trading():
    """
    Subscribes to signals:new (for entries) and price:updates (to track virtual stops/limits and P/L).
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("signals:new", "price:updates")
    
    print("🚀 Paper Trading Engine Started.")
    
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue
            
        channel = message["channel"].decode("utf-8")
        data = json.loads(message["data"].decode("utf-8"))
        
        if channel == "signals:new":
            # Virtual Entry
            config = await db.get_system_config()
            if config.get("paper_trading_enabled", True):
                if data.get("confidence", 0) >= 70:
                    trade = {
                        "symbol": data["symbol"],
                        "type": data["type"],
                        "entry_price": data["entry_price"],
                        "stop_loss": data["stop_loss"],
                        "take_profit": data["take_profit"],
                        "status": "OPEN"
                    }
                    await db.record_trade(trade)
                    print(f"✅ Paper Trade Opened: {trade['type']} {trade['symbol']} at {trade['entry_price']}")
                    
        elif channel == "price:updates":
            # Track P/L and check Stops/Limits
            symbol = data["symbol"]
            current_price = data["price"]
            
            open_trades = await db.get_open_trades(symbol)
            for trade in open_trades:
                pnl = 0
                if trade["type"] == "BUY":
                    pnl = current_price - trade["entry_price"]
                    if current_price <= trade["stop_loss"] or current_price >= trade["take_profit"]:
                        await db.close_trade(trade["_id"], current_price, pnl)
                        print(f"🔒 Paper Trade Closed (BUY): {pnl:.2f}")
                else: # SELL
                    pnl = trade["entry_price"] - current_price
                    if current_price >= trade["stop_loss"] or current_price <= trade["take_profit"]:
                        await db.close_trade(trade["_id"], current_price, pnl)
                        print(f"🔒 Paper Trade Closed (SELL): {pnl:.2f}")

async def start_engine():
    asyncio.create_task(simulate_paper_trading())
