import logging
import math
from typing import Dict, List, Callable
from indicators import IndicatorEngine

logger = logging.getLogger(__name__)

class CandleAggregator:
    def __init__(self, db, redis, symbol="OANDA:XAU_USD"):
        self.db = db
        self.redis = redis
        self.symbol = symbol
        # Timeframes mapping to seconds
        self.timeframes = {
            "M1": 60,
            "M5": 300,
            "M15": 900,
            "M30": 1800,
            "1H": 3600
        }
        
        # State: tf -> dict(timestamp: {open, high, low, close, volume})
        self.current_candles = {tf: None for tf in self.timeframes}
        self.historical_candles = {tf: [] for tf in self.timeframes}
        
    async def load_historical_candles(self):
        """Loads last 100 candles from DB to compute indicators seamlessly."""
        for tf in self.timeframes:
            historic = await self.db.get_recent_candles(self.symbol, tf, 100)
            if historic:
                for h in historic:
                    # Strip mongo _id to standard format
                    h.pop('_id', None)
                    h.pop('created_at', None)
                    h.pop('symbol', None)
                    h.pop('timeframe', None)
                    self.historical_candles[tf].append(h)

    def _get_candle_start(self, timestamp_ms: int, tf_seconds: int) -> int:
        """Rounds timestamp down to the nearest timeframe interval."""
        ts_seconds = timestamp_ms / 1000.0
        start_seconds = math.floor(ts_seconds / tf_seconds) * tf_seconds
        return int(start_seconds * 1000)

    async def process_tick(self, price: float, volume: float, timestamp_ms: int):
        """Called every time a trade tick arrives from websocket."""
        
        for tf, duration_sec in self.timeframes.items():
            candle_start = self._get_candle_start(timestamp_ms, duration_sec)
            
            active = self.current_candles[tf]
            
            # If no active candle, or we crossed cleanly into a new candle boundary
            if not active or candle_start > active["timestamp"]:
                # If we had a previous candle, close it out, calculate indicators and save
                if active:
                    await self._close_candle(tf, active)
                
                # Start new candle
                self.current_candles[tf] = {
                    "timestamp": candle_start,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume
                }
            else:
                # Update current active candle
                active["high"] = max(active["high"], price)
                active["low"] = min(active["low"], price)
                active["close"] = price
                active["volume"] += volume
                
    async def _close_candle(self, tf: str, closed_candle: dict):
        """Closes a candle, attaches indicators, saves to DB, publishes to Redis."""
        # Calculate indicators
        working_list = self.historical_candles[tf] + [closed_candle]
        indicators = IndicatorEngine.calculate(working_list)
        
        if indicators:
            closed_candle["indicators"] = indicators
            
        # Manage memory list
        self.historical_candles[tf].append(closed_candle)
        if len(self.historical_candles[tf]) > 100:
            self.historical_candles[tf].pop(0)
            
        # Store in DB
        await self.db.insert_candle(self.symbol, tf, closed_candle)
        
        # Publish
        await self.redis.publish_candle(self.symbol, tf, closed_candle)
        logger.debug(f"Closed {tf} candle for {self.symbol}: {closed_candle['close']}")
