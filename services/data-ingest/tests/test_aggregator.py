import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from candle_aggregator import CandleAggregator
from indicators import IndicatorEngine

@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get_recent_candles = AsyncMock(return_value=[])
    db.insert_candle = AsyncMock()
    return db

@pytest.fixture
def mock_redis():
    redis = MagicMock()
    redis.publish_candle = AsyncMock()
    return redis

@pytest.mark.asyncio
async def test_aggregator_candle_creation(mock_db, mock_redis):
    aggregator = CandleAggregator(mock_db, mock_redis, "XAU_USD")
    
    # Simulate ticks within the first minute
    await aggregator.process_tick(100.0, 1.0, 60000) # Open
    await aggregator.process_tick(105.0, 2.0, 65000) # High
    await aggregator.process_tick(95.0, 1.5, 90000)  # Low
    await aggregator.process_tick(102.0, 3.0, 119999) # Close
    
    # Check active candle state
    active = aggregator.current_candles["M1"]
    assert active is not None
    assert active["open"] == 100.0
    assert active["high"] == 105.0
    assert active["low"] == 95.0
    assert active["close"] == 102.0
    assert active["volume"] == 7.5
    
    # Tick in next minute should close the M1 candle
    await aggregator.process_tick(103.0, 1.0, 120000)
    
    # Verify db and redis were called
    mock_db.insert_candle.assert_called()
    mock_redis.publish_candle.assert_called()

def test_indicator_engine():
    # Need at least 21 generated dummy candles to verify indicators
    candles = []
    base_price = 2000.0
    for i in range(25):
        # Create an upward trend
        price = base_price + (i * 5)
        candles.append({
            "timestamp": 1600000000000 + (i * 60000),
            "open": price - 2,
            "high": price + 5,
            "low": price - 5,
            "close": price,
            "volume": 10
        })
        
    result = IndicatorEngine.calculate(candles)
    
    # Given an upward trend, RSI should be high and EMA should exist
    assert result is not None
    assert "rsi" in result
    assert "macd" in result
    assert "ema_9" in result
    assert "bb" in result
    
    assert result["ema_9"] > 0
    assert result["rsi"] > 50  # Upward trend means RSI is bullish
