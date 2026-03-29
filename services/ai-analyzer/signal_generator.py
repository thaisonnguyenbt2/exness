import time
import asyncio
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
        self.last_shark_alert = 0
        self.last_highlight_alert = 0

    async def connect(self):
        try:
            await self.redis_client.ping()
            logger.info("Signal generator connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")

    async def process_candle_update(self, symbol: str, candle: dict, tf: str):
        """Called when a new candle closes via Redis."""
        try:
            import aiohttp
            logger.info(f"Triggering Multi-Timeframe AI Analysis for {symbol} at ${candle['close']} (Trigger: {tf})")
            
            # Fetch contextual timeframes completely infinitely directly from MongoDB clusters
            m1_candles, m5_candles, m15_candles, m30_candles = await asyncio.gather(
                self.db.get_recent_candles(symbol, "M1", 200),
                self.db.get_recent_candles(symbol, "M5", 200),
                self.db.get_recent_candles(symbol, "M15", 200),
                self.db.get_recent_candles(symbol, "M30", 200)
            )
            
            analysis = await self.analyzer.analyze_multi_timeframe(
                symbol=symbol,
                m1_candles=m1_candles,
                m5_candles=m5_candles,
                m15_candles=m15_candles,
                m30_candles=m30_candles
            )
            
            if tf == "M5" and m5_candles and len(m5_candles) >= 20:
                await self._check_big_shark(symbol, m5_candles)
                
                # Intercept Highlights real-time
                if analysis and analysis.get("highlight") and "CHÚ Ý" in analysis.get("highlight"):
                    now = time.time()
                    if now - self.last_highlight_alert > 900: # 15-minute cooldown limit
                        self.last_highlight_alert = now
                        alert = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "symbol": symbol,
                            "timeframe": "M5",
                            "type": "HIGHLIGHT",
                            "message": f"🎯 CẢNH BÁO TỚI VÙNG THANH KHOẢN:\n{analysis['highlight']}"
                        }
                        await self.redis_client.publish("signals:new", json.dumps(alert))
            
            if analysis:
                logger.info(f"Analysis complete: {analysis['signal']} (Conf: {analysis.get('confidence')}%)")
                
                live_payload = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "symbol": symbol,
                    "analysis": analysis
                }
                await self.redis_client.publish("analysis:live", json.dumps(live_payload))
                
                # Check Scenarios rigorously against the structured SMC arrays
                smc = analysis.get("smc_data", {})
                scenario = None
                
                if smc.get("choch") and smc.get("fvg_present"):
                    scenario = "SCENARIO_A"
                elif smc.get("bos") and smc.get("htf_alignment"):
                    scenario = "SCENARIO_B"
                elif smc.get("sweep_detected"):
                    scenario = "SCENARIO_C"
                
                if scenario:
                    now = time.time()
                    # 15-minute global cooldown for Scenarios to rigorously prevent duplicate back-to-back triggers during complex grinds
                    if not hasattr(self, 'last_scenario_alert'):
                        self.last_scenario_alert = 0
                        
                    if now - self.last_scenario_alert > 900:
                        self.last_scenario_alert = now
                        report_doc = {
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "symbol": symbol,
                            "timeframe": tf,
                            "type": "SMC_ALERT",
                            "scenario": scenario,
                            "confidence": analysis.get('confidence', 0),
                            "entry_price": analysis.get('entry_price', 0),
                            "stop_loss": analysis.get('stop_loss', 0),
                            "take_profit": analysis.get('take_profit', 0),
                            "liquidity_zones": analysis.get("liquidity_zones", {}),
                            "highlight": analysis.get("highlight", ""),
                            "stats": analysis.get("stats", {}),
                            "smc_data": smc,
                            "ai_analysis": {
                                "trend": analysis.get('trend', 'ranging'),
                                "reasoning": analysis.get('reasoning', '')
                            }
                        }
                        await self.redis_client.publish("signals:new", json.dumps(report_doc))
                        logger.info(f"Published {scenario} SMC Alert to Telegram: {symbol}")
                else:
                    if analysis.get('signal') in ['BUY', 'SELL'] and analysis.get('confidence', 0) >= 70:
                        await self._handle_actionable_signal(symbol, tf, analysis)

                # ── 15-minute market update (always, regardless of scenario) ──────────
                if tf == "M15":
                    smc_data = analysis.get("smc_data", {})
                    lz       = analysis.get("liquidity_zones", {})
                    stats    = analysis.get("stats", {})
                    trend    = analysis.get("trend", "ranging")
                    price    = analysis.get("entry_price", 0)

                    # Build human-readable "what could happen next" outlook
                    outlook_lines = []
                    if smc_data.get("sweep_detected"):
                        outlook_lines.append("🪤 Liquidity has been swept — watch for a sharp reversal off the nearest Order Block.")
                    if smc_data.get("choch"):
                        outlook_lines.append("🔄 Change of Character (ChoCh) detected — momentum may be shifting direction.")
                    if smc_data.get("bos"):
                        outlook_lines.append("✅ Break of Structure (BOS) confirmed — trend continuation trade is the primary scenario.")
                    if smc_data.get("fvg_present"):
                        outlook_lines.append("⚡ Fair Value Gap (FVG / imbalance) is open — price likely to revisit the gap before the next leg.")
                    if not outlook_lines:
                        if trend.lower() == "bullish":
                            outlook_lines.append("📈 Market is consolidating above structure — look for a bullish continuation on the next impulse.")
                        elif trend.lower() == "bearish":
                            outlook_lines.append("📉 Market is consolidating below structure — bearish bias; watch for a retest of the breakdown zone.")
                        else:
                            outlook_lines.append("➡️ No clear SMC signal yet — price is in accumulation/distribution phase. Stay patient.")

                    # Add key level highlights
                    if smc_data.get("poi_zone"):
                        outlook_lines.append(f"🎯 Key POI/OB to watch: ${float(smc_data['poi_zone']):.2f}")

                    update_doc = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "symbol":    symbol,
                        "type":      "UPDATE",
                        "price":     price,
                        "trend":     trend,
                        "structure_m5":  smc_data.get("structure_m5", "N/A"),
                        "structure_m15": smc_data.get("structure_m15", "N/A"),
                        "htf_alignment": smc_data.get("htf_alignment", False),
                        "sweep":     smc_data.get("sweep_detected", False),
                        "bos":       smc_data.get("bos", False),
                        "choch":     smc_data.get("choch", False),
                        "fvg":       smc_data.get("fvg_present", False),
                        "poi_zone":  smc_data.get("poi_zone", None),
                        "stats":     stats,
                        "liquidity_zones": lz,
                        "outlook":   outlook_lines,
                        "reasoning": analysis.get("reasoning", ""),
                        "budget":    float(os.getenv("BUDGET", "500")),
                    }
                    await self.redis_client.publish("signals:new", json.dumps(update_doc))
                    logger.info(f"Published 15m market UPDATE for {symbol} @ ${price}")


        except Exception as e:
            logger.error(f"Error processing candle update natively: {e}")

    async def _check_big_shark(self, symbol: str, m5_candles: list):
        """Mathematically detects massive institutional volume anomalies exactly on the M5 scope"""
        recent = m5_candles[-1]
        prev_19 = m5_candles[-20:-1]
        avg_vol = sum(c['volume'] for c in prev_19) / 19 if prev_19 else 1
        avg_body = sum(abs(c['open'] - c['close']) for c in prev_19) / 19 if prev_19 else 0.1
        
        body = abs(recent['open'] - recent['close'])
        
        # Shark Math Thresholds (User approved: 300% Volume Spike + 200% average structural width + absolute size > $1.5)
        if recent['volume'] > avg_vol * 3.0 and body > avg_body * 2.0 and body > 1.5:
            direction = "TĂNG MẠNH (Mua gom)" if recent['close'] > recent['open'] else "GIẢM SÂU (Bán tháo)"
            now = time.time()
            if now - self.last_shark_alert > 300:  # 5 Minute alert threshold
                self.last_shark_alert = now
                alert = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "symbol": symbol,
                    "type": "SHARK",
                    "message": f"🦈 CÁ MẬP XUẤT HIỆN: Cú sốc Volume cực lớn!\n• Hướng: {direction}\n• Nến M5 (Giá): ${recent['close']:.2f}\n• Kéo giãn: ${body:.2f} (Gấp {body/avg_body:.1f} lần TB)\n• Đột biến Volume: {recent['volume']:.0f} (Gấp {recent['volume']/avg_vol:.1f} lần)"
                }
                await self.redis_client.publish("signals:new", json.dumps(alert))

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
        """Starts a Redis pubsub listener for M5 and M15 candle closes."""
        pubsub = self.redis_client.pubsub()
        # Listen to M5 and M15 implicitly to optimally trigger robust M5 filters explicitly
        await pubsub.subscribe("candles:M5", "candles:M15")
        
        logger.info("Listening for dynamic candles:M5 and M15 on Redis...")
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    channel = message["channel"]
                    tf = channel.split(":")[1] if ":" in channel else "M5"
                    
                    data = json.loads(message["data"])
                    symbol = data.get("symbol")
                    candle = data.get("candle")
                    if symbol and candle:
                        import asyncio
                        asyncio.create_task(self.process_candle_update(symbol, candle, tf))
                except Exception as e:
                    logger.error(f"Error parsing pubsub message: {e}") 

    async def close(self):
        await self.redis_client.close()
