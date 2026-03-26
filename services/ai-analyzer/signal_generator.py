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

    async def process_candle_update(self, symbol: str, m5_candle: dict):
        """Called when a new M5 candle closes via Redis."""
        now = time.time()
        
        if now - self.last_analysis_time < self.cooldown_seconds:
            return
            
        if self.analyzing:
            return
            
        self.analyzing = True
        try:
            import aiohttp
            logger.info(f"Triggering Multi-Timeframe AI Analysis for {symbol} at ${m5_candle['close']}")
            
            # Fetch contextual timeframes from data-ingest in-memory API
            m5_candles = []
            m15_candles = []
            m30_candles = []
            
            async with aiohttp.ClientSession() as session:
                async def fetch_tf(tf):
                    try:
                        async with session.get(f"http://data-ingest:8080/api/v1/candles?timeframe={tf}&limit=20") as resp:
                            data = await resp.json()
                            return data.get("candles", [])
                    except Exception:
                        return []
                
                m5_candles, m15_candles, m30_candles = await asyncio.gather(
                    fetch_tf("M5"), fetch_tf("M15"), fetch_tf("M30")
                )
            
            analysis = await self.analyzer.analyze_multi_timeframe(
                symbol=symbol,
                m5_candles=m5_candles,
                m15_candles=m15_candles,
                m30_candles=m30_candles
            )
            
            if analysis:
                logger.info(f"Analysis complete: {analysis['signal']} (Conf: {analysis.get('confidence')}%)")
                
                # We always publish the active analysis to Redis so the Frontend UI can stream it Live
                live_payload = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "symbol": symbol,
                    "analysis": analysis
                }
                await self.redis_client.publish("analysis:live", json.dumps(live_payload))
                
                # If confidence > 70% and not WAIT, it's actionable trading signal
                if analysis.get('signal') in ['BUY', 'SELL'] and analysis.get('confidence', 0) >= 70:
                    await self._handle_actionable_signal(symbol, "M5", analysis)
            
            self.last_analysis_time = time.time()
            
        except Exception as e:
            logger.error(f"Error processing candle update: {e}")
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
            logger.info(f"Published new actionable signal: {signal_doc['type']} {symbol}")

    async def start_listening(self):
        """Starts a Redis pubsub listener for M5 candle closes."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("candles:M5")
        
        logger.info("Listening for candles:M5 on Redis...")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    symbol = data.get("symbol")
                    candle = data.get("candle")
                    if symbol and candle:
                        # Offload to task without blocking the pubsub loop
                        import asyncio
                        asyncio.create_task(self.process_candle_update(symbol, candle))
                except Exception as e:
                    logger.error(f"Error parsing pubsub message: {e}") 

    async def close(self):
        await self.redis_client.close()
