import time
import json
import logging
from datetime import datetime
from db import DatabaseSchema
from analyzer import GeminiAnalyzer
import redis.asyncio as redis
import os

logger = logging.getLogger(__name__)

class SignalGenerator:
    def __init__(self, db: DatabaseSchema):
        self.db = db
        self.analyzer = GeminiAnalyzer()
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        self.last_analysis_time = 0
        self.cooldown_seconds = 30
        self.analyzing = False

    async def connect(self):
        try:
            await self.redis_client.ping()
            logger.info("Signal generator connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

    async def process_price_update(self, symbol: str, current_price: float):
        """Called when a new price tick arrives from Redis."""
        now = time.time()
        
        # Cooldown check
        if now - self.last_analysis_time < self.cooldown_seconds:
            return
            
        # Prevent concurrent analysis storms
        if self.analyzing:
            return
            
        self.analyzing = True
        try:
            # We perform analysis on the M5 timeframe as a standard anchor.
            timeframe = "M5"
            candles = await self.db.get_recent_candles(symbol, timeframe, 100)
            
            if not candles or len(candles) < 20:
                logger.warning(f"Not enough candles to analyze {symbol} {timeframe}")
                return
                
            latest_candle = candles[-1]
            
            # Make sure the candle has indicators
            if "indicators" not in latest_candle:
                return

            logger.info(f"Triggering AI Analysis for {symbol} at ${current_price}")
            
            analysis = await self.analyzer.analyze_market(
                symbol=symbol,
                current_price=current_price,
                timeframe=timeframe,
                latest_candle=latest_candle,
                historical_candles=candles
            )
            
            if analysis:
                logger.info(f"Analysis complete: {analysis['signal']} (Conf: {analysis.get('confidence')}%)")
                
                # If confidence > 70% and not WAIT, it's actionable
                if analysis.get('signal') in ['BUY', 'SELL'] and analysis.get('confidence', 0) >= 70:
                    await self._handle_actionable_signal(symbol, timeframe, analysis)
            
            self.last_analysis_time = time.time()
            
        except Exception as e:
            logger.error(f"Error processing price update: {e}")
        finally:
            self.analyzing = False

    async def _handle_actionable_signal(self, symbol: str, timeframe: str, analysis: dict):
        """Saves high confidence signals to DB and broadcasts to Notification service."""
        signal_doc = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "symbol": symbol,
            "timeframe": timeframe,
            "type": analysis["signal"],
            "confidence": analysis["confidence"],
            "entry_price": analysis["entry_price"],
            "stop_loss": analysis["stop_loss"],
            "take_profit": analysis["take_profit"],
            "ai_analysis": {
                "trend": analysis["trend"],
                "reasoning": analysis["reasoning"]
            }
        }
        
        # Save to DB
        signal_id = await self.db.save_signal(signal_doc)
        if signal_id:
            signal_doc["id"] = signal_id
            
            # Publish to Redis so notification service picks it up
            await self.redis_client.publish("signals:new", json.dumps(signal_doc))
            logger.info(f"Published new signal: {signal_doc['type']} {symbol}")

    async def start_listening(self):
        """Starts a Redis pubsub listener for price updates."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("price:updates")
        
        logger.info("Listening for price:updates on Redis...")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    symbol = data.get("symbol")
                    price = data.get("price")
                    if symbol and price:
                        await self.process_price_update(symbol, price)
                except Exception as e:
                    logger.error(f"Error parsing pubsub message: {e}") 

    async def close(self):
        await self.redis_client.close()
