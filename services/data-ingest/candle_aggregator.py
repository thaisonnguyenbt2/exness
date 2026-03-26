import logging
import math
from typing import Dict, List, Callable
from indicators import IndicatorEngine

logger = logging.getLogger(__name__)

class CandleAggregator:
    def __init__(self, redis_pub, symbol="OANDA:XAU_USD"):
        self.redis = redis_pub
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
        """Loads last 100 candles from Finnhub REST to compute indicators seamlessly."""
        import os
        import time
        import aiohttp
        
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            logger.warning("No FINNHUB_API_KEY, cannot load history")
            return
            
        to_time = int(time.time())
        from_time = to_time - (3 * 24 * 60 * 60) # Last 3 days to get enough M30 candles
        
        # Map our timeframe to Finnhub resolution
        resolution_map = {"M1": "1", "M5": "5", "M15": "15", "M30": "30", "1H": "60"}

        async with aiohttp.ClientSession() as session:
            for tf in self.timeframes:
                res = resolution_map.get(tf, "1")
                url = f"https://finnhub.io/api/v1/forex/candle?symbol={self.symbol}&resolution={res}&from={from_time}&to={to_time}&token={api_key}"
                
                try:
                    async with session.get(url) as response:
                        data = await response.json()
                        if data and data.get("s") == "ok":
                            candles = []
                            for i in range(len(data['t'])):
                                vol = data.get('v', [0]*len(data['t']))[i] if data.get('v') else 0
                                c = {
                                    "timestamp": data['t'][i] * 1000,
                                    "open": data['o'][i],
                                    "high": data['h'][i],
                                    "low": data['l'][i],
                                    "close": data['c'][i],
                                    "volume": vol
                                }
                                candles.append(c)
                            
                            # Keep last 100
                            self.historical_candles[tf] = candles[-100:]
                            
                            # Pre-calculate indicators on history sequentially
                            working_list = []
                            for idx, c in enumerate(self.historical_candles[tf]):
                                working_list.append(c.copy())
                                indicators = IndicatorEngine.calculate(working_list)
                                if indicators:
                                    self.historical_candles[tf][idx]["indicators"] = indicators
                                    
                            logger.info(f"Loaded {len(self.historical_candles[tf])} historical candles for {tf}")
                        else:
                            logger.warning(f"Failed to fetch history for {tf}: {data}")
                except Exception as e:
                    logger.error(f"Error fetching historical data for {tf}: {e}")

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
            
        # Publish
        await self.redis.publish_candle(self.symbol, tf, closed_candle)
        logger.debug(f"Closed {tf} candle for {self.symbol}: {closed_candle['close']}")
