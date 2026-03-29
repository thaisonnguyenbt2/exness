import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger(__name__)

class IndicatorEngine:
    """Calculates technical indicators on a list of candlesticks using pandas-ta."""
    
    @staticmethod
    def calculate(candles: list) -> dict:
        """
        Takes a list of standard OHLCV candle dicts and returns the indicators
        for the most recent candle.
        """
        if not candles or len(candles) < 21:  # Need enough data for EMA/BB/ADX
            return None
            
        try:
            df = pd.DataFrame(candles)
            
            # Ensure columns are numeric
            df['open'] = pd.to_numeric(df['open'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['close'] = pd.to_numeric(df['close'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # RSI (14)
            df.ta.rsi(length=14, append=True)
            
            # MACD (12, 26, 9)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            
            # Bollinger Bands (20, 2)
            df.ta.bbands(length=20, std=2, append=True)
            
            # EMA (9), EMA (21)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            
            # ADX (14)
            df.ta.adx(length=14, append=True)
            
            # Get latest row
            latest = df.iloc[-1]
            
            # Extract indicators (pandas_ta names columns dynamically)
            rsi = float(latest.get('RSI_14', 0))
            
            macd_val = float(latest.get('MACD_12_26_9', 0))
            macd_signal = float(latest.get('MACDs_12_26_9', 0))
            macd_hist = float(latest.get('MACDh_12_26_9', 0))
            
            bb_lower = float(latest.get('BBL_20_2.0_2.0', 0))
            bb_middle = float(latest.get('BBM_20_2.0_2.0', 0))
            bb_upper = float(latest.get('BBU_20_2.0_2.0', 0))
            
            ema9 = float(latest.get('EMA_9', 0))
            ema21 = float(latest.get('EMA_21', 0))
            
            adx = float(latest.get('ADX_14', 0))
            
            return {
                "rsi": rsi,
                "macd": {
                    "value": macd_val,
                    "signal": macd_signal,
                    "histogram": macd_hist
                },
                "bb": {
                    "upper": bb_upper,
                    "middle": bb_middle,
                    "lower": bb_lower
                },
                "ema_9": ema9,
                "ema_21": ema21,
                "adx": adx
            }
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return None
