import os
import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY environment variable is not set. AI Analysis will fail.")
        else:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                'gemini-1.5-flash',
                system_instruction="You are an expert XAU/USD gold trader. Respond ONLY with valid JSON."
            )

    async def analyze_market(self, symbol: str, current_price: float, timeframe: str, latest_candle: dict, historical_candles: list) -> dict:
        """Calls Gemini to analyze the market based on technical indicators and history."""
        if not self.api_key:
            return None
            
        try:
            indicators = latest_candle.get("indicators", {})
            candles_json = json.dumps([{
                "time": c["timestamp"], 
                "close": c["close"], 
                "vol": c["volume"]
            } for c in historical_candles[-20:]], indent=2)

            prompt = f"""
Analyze this {symbol} market data and provide trading signal:

Current Price: ${current_price}
Timeframe: {timeframe}

Technical Indicators:
- RSI(14): {indicators.get('rsi', 'N/A')} (Overbought: >70, Oversold: <30)
- MACD: {indicators.get('macd', {}).get('value', 'N/A')}, Signal: {indicators.get('macd', {}).get('signal', 'N/A')}, Histogram: {indicators.get('macd', {}).get('histogram', 'N/A')}
- Bollinger Bands: Upper ${indicators.get('bb', {}).get('upper', 'N/A')}, Middle ${indicators.get('bb', {}).get('middle', 'N/A')}, Lower ${indicators.get('bb', {}).get('lower', 'N/A')}
- EMA(9): ${indicators.get('ema_9', 'N/A')}, EMA(21): ${indicators.get('ema_21', 'N/A')}
- ADX: {indicators.get('adx', 'N/A')} (Trend strength)

Recent Candles (last 20):
{candles_json}

Provide analysis strictly in JSON format matching this structure:
{{
  "trend": "bullish|bearish|ranging",
  "signal": "BUY|SELL|WAIT",
  "confidence": 0-100,
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "reasoning": "brief explanation"
}}
"""
            
            # Using generate_content_async for async operations
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )
            
            text = response.text
            
            # Clean up standard JSON formatting if any
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
                
            result = json.loads(text)
            return result
            
        except Exception as e:
            logger.error(f"Error calling Gemini AI: {e}", exc_info=True)
            return None
