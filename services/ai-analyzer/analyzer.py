import os
import json
import logging

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    # Renamed functionally to QuantAnalyzer but keeping class name to prevent breaking imports in signal_generator.py
    def __init__(self):
        logger.info("Initializing Pure Quantitative Algorithmic Engine (Bypassing Gemini)")

    async def analyze_multi_timeframe(self, symbol: str, m1_candles: list, m5_candles: list, m15_candles: list, m30_candles: list) -> dict:
        """Analyzes the market based on multi-timeframe technicals purely computationally without an LLM."""
        try:
            if not m15_candles or len(m15_candles) < 20: 
                return None

            current_price = m1_candles[-1]['close'] if m1_candles else m5_candles[-1]['close'] if m5_candles else m15_candles[-1]['close']
            
            latest_m15 = m15_candles[-1]
            ind_m15 = latest_m15.get("indicators", {})
            rsi_m15 = ind_m15.get('rsi', 50)
            ema9_m15 = ind_m15.get('ema_9', current_price)
            ema21_m15 = ind_m15.get('ema_21', current_price)
            
            latest_m5 = m5_candles[-1]
            ind_m5 = latest_m5.get("indicators", {})
            rsi_m5 = ind_m5.get('rsi', 50)
            ema9_m5 = ind_m5.get('ema_9', current_price)
            ema21_m5 = ind_m5.get('ema_21', current_price)

            def analyze_smc(candles):
                if not candles or len(candles) < 20:
                    return {"type": "RANGING", "sweep": False, "poi": None, "fvg": False, "direction": None, "bos": False, "choch": False}
                
                # 1. Identify Fractals (Swing Highs / Lows)
                highs, lows = [], []
                for i in range(2, len(candles)-2):
                    c = candles[i]
                    if c['high'] > candles[i-1]['high'] and c['high'] > candles[i-2]['high'] and c['high'] > candles[i+1]['high'] and c['high'] > candles[i+2]['high']:
                        highs.append((i, c))
                    if c['low'] < candles[i-1]['low'] and c['low'] < candles[i-2]['low'] and c['low'] < candles[i+1]['low'] and c['low'] < candles[i+2]['low']:
                        lows.append((i, c))
                        
                if not highs or not lows:
                    return {"type": "RANGING", "sweep": False, "poi": None, "fvg": False, "direction": None, "bos": False, "choch": False}

                last_h = highs[-1][1]
                last_l = lows[-1][1]
                prev_h = highs[-2][1] if len(highs) > 1 else last_h
                prev_l = lows[-2][1] if len(lows) > 1 else last_l
                
                # Determine Prior Structure Direction
                structure_dir = "BULLISH" if last_h['high'] > prev_h['high'] and last_l['low'] > prev_l['low'] else "BEARISH" if last_h['high'] < prev_h['high'] and last_l['low'] < prev_l['low'] else "RANGING"
                
                recent_candle = candles[-1]
                recent_close = recent_candle['close']
                recent_high = recent_candle['high']
                recent_low = recent_candle['low']
                
                bos, choch, sweep = False, False, False
                direction = None
                poi = None
                
                # 2. BOS / ChoCh & Sweeps Detection
                if recent_high > last_h['high']:
                    if recent_close > last_h['high']:
                        if structure_dir == "BULLISH":
                            bos, direction = True, "BULLISH"
                        else:
                            choch, direction = True, "BULLISH"
                    else:
                        sweep, direction = True, "BEARISH_TRAP"
                        
                elif recent_low < last_l['low']:
                    if recent_close < last_l['low']:
                        if structure_dir == "BEARISH":
                            bos, direction = True, "BEARISH"
                        else:
                            choch, direction = True, "BEARISH"
                    else:
                        sweep, direction = True, "BULLISH_TRAP"

                # 3. Order Block & FVG Detection
                fvg_present = False
                if bos or choch:
                    for i in range(len(candles)-5, len(candles)-1):
                        c1, c3 = candles[i-1], candles[i+1]
                        if direction == "BULLISH" and c1['high'] < c3['low']:
                            fvg_present = True
                            for j in range(i, max(0, i-10), -1):
                                if candles[j]['close'] < candles[j]['open']:
                                    poi = candles[j]['low']
                                    break
                            break
                        elif direction == "BEARISH" and c1['low'] > c3['high']:
                            fvg_present = True
                            for j in range(i, max(0, i-10), -1):
                                if candles[j]['close'] > candles[j]['open']:
                                    poi = candles[j]['high']
                                    break
                            break

                return {
                    "type": "BOS" if bos else "CHOCH" if choch else "SWEEP" if sweep else "RANGING",
                    "direction": direction,
                    "bos": bos,
                    "choch": choch,
                    "sweep": sweep,
                    "poi": poi,
                    "fvg": fvg_present
                }

            # Inject Deep SMC Evaluation
            smc_m15 = analyze_smc(m15_candles)
            smc_m5 = analyze_smc(m5_candles)
            
            # Base Trend Detection (Dual-Tier M15 & M5)
            trend = "ranging"
            confidence = 50
            
            m15_bull = ema9_m15 > ema21_m15 and rsi_m15 > 55
            m15_bear = ema9_m15 < ema21_m15 and rsi_m15 < 45
            
            m5_bull = ema9_m5 > ema21_m5 and rsi_m5 > 55
            m5_bear = ema9_m5 < ema21_m5 and rsi_m5 < 45

            if m15_bull:
                trend = "bullish"
                confidence += 20
            elif m15_bear:
                trend = "bearish"
                confidence += 20
            elif m5_bull:
                trend = "bullish"  # Rapid M5 Breakout
                confidence += 10
            elif m5_bear:
                trend = "bearish"  # Rapid M5 Breakdown
                confidence += 10
            
            # SMC HTF Confluence Override
            htf_alignment = False
            if (smc_m5["direction"] == "BULLISH" and m15_bull) or (smc_m5["direction"] == "BEARISH" and m15_bear):
                htf_alignment = True

            def extract_liquidity(candles):
                if not candles or len(candles) < 20:
                    return {"bfvg": None, "sfvg": None, "sup": current_price, "res": current_price}
                h = max([c['high'] for c in candles[-20:]])
                l = min([c['low'] for c in candles[-20:]])
                bfvg, sfvg = None, None
                for i in range(len(candles) - 1, 2, -1):
                    c1, c2, c3 = candles[i-2], candles[i-1], candles[i]
                    if c1['high'] < c3['low']:
                        bfvg = (c1['high'], c3['low'])
                        break
                    elif c1['low'] > c3['high']:
                        sfvg = (c3['high'], c1['low'])
                        break
                return {"bfvg": bfvg, "sfvg": sfvg, "sup": l, "res": h}

            zones_data = {
                "M5": extract_liquidity(m5_candles),
                "M15": extract_liquidity(m15_candles),
                "M30": extract_liquidity(m30_candles)
            }
            
            liquidity_zones_str = {}
            highlight_msg = None

            for tf, z in zones_data.items():
                liquidity_zones_str[tf] = {
                    "bfvg": f"${z['bfvg'][1]:.2f} (Điểm vào Mưa/Buy Limit)" if z['bfvg'] else None,
                    "sfvg": f"${z['sfvg'][0]:.2f} (Điểm vào Bán/Sell Limit)" if z['sfvg'] else None,
                    "sup": f"${z['sup']:.2f}",
                    "res": f"${z['res']:.2f}"
                }
                
                # Check proximities for limits (Within $1.5 padding)
                if highlight_msg is None:
                    if z['bfvg'] and 0 < (current_price - z['bfvg'][1]) <= 1.5:
                        highlight_msg = f"🚨 CHÚ Ý: Giá đang tiến rất gần vùng Bullish FVG {tf} tại {bfstr}. Xem xét CANH MUA (Buy Limit) tại ${z['bfvg'][1]:.2f}, Dừng lỗ ${z['bfvg'][0]-1.0:.2f}."
                    elif z['sfvg'] and 0 < (z['sfvg'][0] - current_price) <= 1.5:
                        highlight_msg = f"🚨 CHÚ Ý: Giá đang chạm ngưỡng Bearish FVG {tf} tại {sfstr}. Xem xét CANH BÁN (Sell Limit) tại ${z['sfvg'][0]:.2f}, Dừng lỗ ${z['sfvg'][1]+1.0:.2f}."
                    elif 0 <= (current_price - z['sup']) <= 1.0:
                        highlight_msg = f"🚨 CHÚ Ý: Giá đang rà đáy Support {tf} tại ${z['sup']:.2f}."
                    elif 0 <= (z['res'] - current_price) <= 1.0:
                        highlight_msg = f"🚨 CHÚ Ý: Giá đang chạm đỉnh Resistance {tf} tại ${z['res']:.2f}."

            if highlight_msg is None:
                highlight_msg = "Giá hiện tại đang lơ lửng, chưa tiếp cận vùng thanh khoản quan trọng nào. Cần kiên nhẫn."

            # Vietnamese Rationale
            reasoning = f"Giá hiện tại đang ở mức ${current_price:.2f}. "
            if trend == "bullish":
                buy_target = zones_data["M15"]["bfvg"][1] if zones_data["M15"]["bfvg"] else zones_data["M15"]["sup"]
                if m15_bull:
                    reasoning += f"Cấu trúc M15 đang TĂNG. Khuyến nghị đặt lệnh BUY LIMIT chính xác tại ${buy_target:.2f} (Cạnh trên cấu trúc thanh khoản M15)."
                else:
                    reasoning += f"M15 đi ngang nhưng M5 bứt phá TĂNG. Lực đẩy ngắn hạn đang mạnh, rải BUY LIMIT quanh mốc ${buy_target:.2f}."
                signal = "BUY"
            elif trend == "bearish":
                sell_target = zones_data["M15"]["sfvg"][0] if zones_data["M15"]["sfvg"] else zones_data["M15"]["res"]
                if m15_bear:
                    reasoning += f"Cấu trúc M15 đang GIẢM. Khuyến nghị đặt lệnh SELL LIMIT chính xác tại ${sell_target:.2f} (Cạnh dưới cấu trúc thanh khoản M15)."
                else:
                    reasoning += f"M15 đi ngang nhưng M5 gãy đổ GIẢM. Áp lực bán xuất hiện, rải SELL LIMIT quanh mốc ${sell_target:.2f}."
                signal = "SELL"
            else:
                reasoning += f"Hai khung M15/M5 đều đi ngang (RSI M15={rsi_m15:.0f}). Đứng ngoài quan sát, chỉ giao dịch nếu giá quét qua biên ${zones_data['M15']['sup']:.2f} hoặc ${zones_data['M15']['res']:.2f}."
                signal = "WAIT"
                confidence = 0

            # Compute simple moving averages for M15 candles
            ma20 = None
            ma50 = None
            if len(m15_candles) >= 20:
                ma20 = round(sum(c['close'] for c in m15_candles[-20:]) / 20, 2)
            if len(m15_candles) >= 50:
                ma50 = round(sum(c['close'] for c in m15_candles[-50:]) / 50, 2)

            bb_m15 = ind_m15.get('bb', {})
            macd_m15 = ind_m15.get('macd', {})
            stats = {
                "rsi": round(rsi_m15, 2),
                "bb_upper": round(bb_m15.get("upper", 0), 2),
                "bb_middle": round(bb_m15.get("middle", 0), 2),
                "bb_lower": round(bb_m15.get("lower", 0), 2),
                "macd_val": round(macd_m15.get("value", 0), 4),
                "macd_signal": round(macd_m15.get("signal", 0), 4),
                "ma20": ma20,
                "ma50": ma50,
            }

            smc_output = {
                "structure_m15": smc_m15["type"],
                "structure_m5": smc_m5["type"],
                "direction": smc_m5["direction"],
                "htf_alignment": htf_alignment,
                "fvg_present": smc_m5["fvg"],
                "poi_zone": round(smc_m5["poi"], 2) if smc_m5["poi"] else None,
                "sweep_detected": smc_m5["sweep"]
            }

            return {
                "trend": trend,
                "signal": signal,
                "confidence": min(100, int(confidence)),
                "entry_price": round(float(current_price), 2),
                "stop_loss": round(float(zones_data["M30"]["sup"] - 2.0), 2),
                "take_profit": round(float(zones_data["M30"]["res"] + 5.0), 2),
                "reasoning": reasoning,
                "highlight": highlight_msg,
                "liquidity_zones": liquidity_zones_str,
                "stats": stats,
                "smc_data": smc_output
            }
            
        except Exception as e:
            logger.error(f"Error computing Quant algorithmic matrices: {e}", exc_info=True)
            return None
