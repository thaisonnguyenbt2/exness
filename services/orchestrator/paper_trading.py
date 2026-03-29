"""
Paper Trading Engine — $500 Budget Edition
============================================
Budget   : $500
Risk/trade: 2% = $10
RR ratio : 1:2 → TP = entry ± 2×stop_distance
Position : size = $10 / abs(entry - stop)

Redis events published
----------------------
trade:pre_order   – about to place the order
trade:filled      – order conceptually filled at entry_price
trade:closed      – trade closed at TP or SL
"""

import json
import asyncio
import redis.asyncio as redis
import os
from db import db
from datetime import datetime, timezone

REDIS_URL   = os.getenv("REDIS_URL", "redis://localhost:6379")
BUDGET      = float(os.getenv("BUDGET", "500"))
RISK_PCT    = float(os.getenv("RISK_PERCENT", "2"))  # %
MIN_CONFIDENCE = 70

redis_client = redis.from_url(REDIS_URL)

# ── helpers ────────────────────────────────────────────────────────────────

def risk_amount() -> float:
    return BUDGET * (RISK_PCT / 100)          # $10 at $500 / 2%

def calc_position_size(entry: float, stop: float) -> float:
    dist = abs(entry - stop)
    if dist == 0:
        return 0.0
    return round(risk_amount() / dist, 6)

def calc_take_profit(direction: str, entry: float, stop: float) -> float:
    dist = abs(entry - stop)
    if direction == "BUY":
        return round(entry + 2 * dist, 2)   # 1:2 RR
    return round(entry - 2 * dist, 2)

def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()

async def publish(channel: str, payload: dict):
    await redis_client.publish(channel, json.dumps(payload))

# ── core engine ────────────────────────────────────────────────────────────

async def simulate_paper_trading():
    """
    Subscribes to signals:new (entries) and price:updates (track stops/targets).
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("signals:new", "price:updates")

    print(f"🚀 Paper Trading Engine started  |  Budget: ${BUDGET}  |  Risk/trade: ${risk_amount()}")

    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        channel = message["channel"].decode("utf-8")
        data    = json.loads(message["data"].decode("utf-8"))

        # ── new signal → open virtual trade ───────────────────────────────
        if channel == "signals:new":
            config = await db.get_system_config()
            if not config.get("paper_trading_enabled", True):
                continue
            if data.get("confidence", 0) < MIN_CONFIDENCE:
                continue

            direction   = data.get("type", "BUY").upper()
            if direction not in ("BUY", "SELL"):
                continue

            entry  = float(data.get("entry_price", 0))
            stop   = float(data.get("stop_loss",   0))
            if entry == 0 or stop == 0:
                continue

            tp   = calc_take_profit(direction, entry, stop)
            qty  = calc_position_size(entry, stop)
            risk = risk_amount()

            # 1. Pre-order notification
            pre_order = {
                "event":     "pre_order",
                "symbol":    data["symbol"],
                "direction": direction,
                "entry":     entry,
                "stop":      stop,
                "tp":        tp,
                "qty":       qty,
                "risk":      risk,
                "budget":    BUDGET,
                "scenario":  data.get("scenario", ""),
                "smc_data":  data.get("smc_data", {}),
                "timestamp": now_utc(),
            }
            await publish("trade:pre_order", pre_order)
            print(f"📢 Pre-order  → {direction} {data['symbol']} @ {entry}  SL:{stop}  TP:{tp}  Qty:{qty}")

            # 2. Record and simulate fill (paper = instant)
            trade_doc = {
                "symbol":     data["symbol"],
                "type":       direction,
                "entry_price": entry,
                "stop_loss":  stop,
                "take_profit": tp,
                "qty":        qty,
                "risk":       risk,
                "status":     "OPEN",
            }
            result = await db.record_trade(trade_doc)

            # 3. Filled notification
            filled = {**pre_order, "event": "filled", "trade_id": str(result.inserted_id)}
            await publish("trade:filled", filled)
            print(f"✅ Filled     → {direction} {data['symbol']} @ {entry}")

        # ── price update → check TP / SL ──────────────────────────────────
        elif channel == "price:updates":
            symbol        = data["symbol"]
            current_price = float(data["price"])

            open_trades = await db.get_open_trades(symbol)
            for trade in open_trades:
                direction = trade["type"]
                entry     = trade["entry_price"]
                stop      = trade["stop_loss"]
                tp        = trade["take_profit"]
                qty       = trade.get("qty", 0)
                risk      = trade.get("risk", risk_amount())

                hit_sl = False
                hit_tp = False

                if direction == "BUY":
                    pnl    = (current_price - entry) * qty
                    hit_sl = current_price <= stop
                    hit_tp = current_price >= tp
                else:
                    pnl    = (entry - current_price) * qty
                    hit_sl = current_price >= stop
                    hit_tp = current_price <= tp

                if hit_sl or hit_tp:
                    outcome = "TP" if hit_tp else "SL"
                    await db.close_trade(trade["_id"], current_price, pnl)

                    closed_event = {
                        "event":         "trade_closed",
                        "outcome":       outcome,
                        "symbol":        symbol,
                        "direction":     direction,
                        "entry":         entry,
                        "exit_price":    current_price,
                        "stop":          stop,
                        "tp":            tp,
                        "qty":           qty,
                        "pnl":           round(pnl, 2),
                        "risk":          risk,
                        "budget_after":  round(BUDGET + pnl, 2),
                        "timestamp":     now_utc(),
                    }
                    await publish("trade:closed", closed_event)
                    emoji = "🏆" if hit_tp else "❌"
                    print(f"{emoji} Trade closed ({outcome})  {symbol}  {direction}  exit:{current_price}  P&L:{pnl:+.2f}")


async def start_engine():
    asyncio.create_task(simulate_paper_trading())
