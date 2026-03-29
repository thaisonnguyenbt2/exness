import logging
import math
from typing import Dict, List, Callable
from indicators import IndicatorEngine

logger = logging.getLogger(__name__)

class CandleAggregator:
    def __init__(self, redis_pub, db, symbol="OANDA:XAU_USD"):
        self.redis = redis_pub
        self.db = db
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
        """Loads last 7 days of 1-minute candles from Yahoo Finance to seamlessly bootstrap the SMC historical cache."""
        import yfinance as yf
        import pandas as pd
        import time
        from datetime import datetime, timezone
        
        logger.info(f"Downloading deep 1m historical seed data for Gold via YFinance...")
        
        try:
            # Dynamic mapping for Yahoo Finance
            yf_symbol = "GC=F"
            if "BTC" in self.symbol:
                yf_symbol = "BTC-USD"
            elif "ETH" in self.symbol:
                yf_symbol = "ETH-USD"
                
            # yfinance allows period="5d" with interval="1m" natively
            df = yf.download(yf_symbol, period="5d", interval="1m", progress=False)
            
            if df.empty:
                logger.error(f"YFinance returned empty DataFrame for {yf_symbol}. History mapping failed.")
                return
            
            # Reconstruct the 1M fundamental ticks
            m1_candles = []
            for d in df.itertuples():
                # Handling multi-index columns from yf.download
                # index 0 is Timestamp, High, Low, Open, Close, Volume
                # the tuple looks like Pandas(Index=Timestamp('..'), Close=.. , High=.. , Low=.. , Open=.. , Volume=..)
                # Because yfinance drops Ticker levels in simple pulls, we extract directly
                
                # Ensure timestamp is native UTC millisecond format
                dt = d.Index
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts_ms = int(dt.timestamp() * 1000)
                
                c = {
                    "timestamp": ts_ms,
                    "open": float(getattr(d, "Open", getattr(d, "_3", 0))),
                    "high": float(getattr(d, "High", getattr(d, "_1", 0))),
                    "low": float(getattr(d, "Low", getattr(d, "_2", 0))),
                    "close": float(getattr(d, "Close", getattr(d, "_4", 0))),
                    "volume": float(getattr(d, "Volume", 0))
                }
                if c["close"] > 0:
                    m1_candles.append(c)
            
            logger.info(f"Ingested {len(m1_candles)} raw historic 1-minute candles. Aggregating multi-timeframes...")
            
            # Now artificially 'play' these ticks through our resampler to perfectly build the M5, M15, M30 sets
            # We clear out memory first to ensure clean state
            self.current_candles = {tf: None for tf in self.timeframes}
            self.historical_candles = {tf: [] for tf in self.timeframes}
            
            for base_candle in m1_candles:
                # We inject the M1 close price to sequentially trigger aggregation silently
                await self.process_tick(base_candle["close"], base_candle["volume"], base_candle["timestamp"], publish=False)
                
            for tf in self.timeframes:
                logger.info(f"Buffered {len(self.historical_candles[tf])} verified historical {tf} candles.")
                # Natively push entirely into robust MongoDB schema!
                await self.db.save_candles_bulk(self.symbol, tf, self.historical_candles[tf])
                
        except Exception as e:
            logger.error(f"Error massively injecting YFinance historical data: {e}", exc_info=True)

    def _get_candle_start(self, timestamp_ms: int, tf_seconds: int) -> int:
        """Rounds timestamp down to the nearest timeframe interval."""
        ts_seconds = timestamp_ms / 1000.0
        start_seconds = math.floor(ts_seconds / tf_seconds) * tf_seconds
        return int(start_seconds * 1000)

    async def process_tick(self, price: float, volume: float, timestamp_ms: int, publish: bool = True):
        """Called every time a trade tick arrives from websocket."""
        
        for tf, duration_sec in self.timeframes.items():
            candle_start = self._get_candle_start(timestamp_ms, duration_sec)
            
            active = self.current_candles[tf]
            
            # If no active candle, or we crossed cleanly into a new candle boundary
            if not active or candle_start > active["timestamp"]:
                # If we had a previous candle, close it out, calculate indicators and save
                if active:
                    await self._close_candle(tf, active, publish)
                
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
                
    async def _close_candle(self, tf: str, closed_candle: dict, publish: bool):
        """Closes a candle, attaches indicators, saves to DB, optionally publishes to Redis."""
        # Calculate indicators
        working_list = self.historical_candles[tf] + [closed_candle]
        indicators = IndicatorEngine.calculate(working_list)
        
        if indicators:
            closed_candle["indicators"] = indicators
            
        # Manage memory list
        self.historical_candles[tf].append(closed_candle)
        if len(self.historical_candles[tf]) > 200: # Expanded historical memory to 200 explicitly for deep SMC mapping limits!
            self.historical_candles[tf].pop(0)
            
        # Publish and persistently upsert
        if publish:
            await self.db.save_candle(self.symbol, tf, closed_candle)
            await self.redis.publish_candle(self.symbol, tf, closed_candle)
            logger.debug(f"Closed {tf} candle natively for {self.symbol}: {closed_candle['close']}")
