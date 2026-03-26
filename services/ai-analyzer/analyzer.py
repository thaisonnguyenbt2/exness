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

    async def analyze_multi_timeframe(self, symbol: str, m5_candles: list, m15_candles: list, m30_candles: list) -> dict:
        """Calls Gemini to analyze the market based on multi-timeframe technical indicators."""
        if not self.api_key:
            return None
            
        try:
            def format_tf(candles):
                if not candles: return "No data"
                latest = candles[-1]
                indicators = latest.get("indicators", {})
                return f"""Price: ${latest['close']}
RSI(14): {indicators.get('rsi', 'N/A')}
MACD: {indicators.get('macd', {}).get('value', 'N/A')}, Signal: {indicators.get('macd', {}).get('signal', 'N/A')}
BB: Upper {indicators.get('bb', {}).get('upper', 'N/A')}, Lower {indicators.get('bb', {}).get('lower', 'N/A')}
EMA(9): {indicators.get('ema_9', 'N/A')}, EMA(21): {indicators.get('ema_21', 'N/A')}"""

            m5_info = format_tf(m5_candles)
            m15_info = format_tf(m15_candles)
            m30_info = format_tf(m30_candles)

            prompt = f"""
Analyze this {symbol} market data across multiple timeframes and provide a trading signal:

M5 Timeframe (Short-term context):
{m5_info}

M15 Timeframe (Medium-term context):
{m15_info}

M30 Timeframe (Macro trend context):
{m30_info}

Provide analysis strictly in JSON format matching this structure:
{{
  "trend": "bullish|bearish|ranging",
  "signal": "BUY|SELL|WAIT",
  "confidence": 0-100,
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "reasoning": "multi-timeframe reasoning"
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
