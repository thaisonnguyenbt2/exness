import os
import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import websockets
from websocket_client import FinnhubWSClient
from redis_publisher import RedisPublisher
from candle_aggregator import CandleAggregator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("data-ingest")

app = FastAPI(title="XAU/USD Data Ingestion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SYMBOL = os.getenv("SYMBOL", "OANDA:XAU_USD")

# Global dependencies
redis_pub = RedisPublisher()
aggregator = CandleAggregator(redis_pub, SYMBOL)
ws_client = None
active_connections: list[WebSocket] = []

async def on_tick(price: float, volume: float, timestamp: int):
    # Forward to aggregator
    await aggregator.process_tick(price, volume, timestamp)
    # Publish to internal services
    await redis_pub.publish_price_update(SYMBOL, price, timestamp)
    
    # Broadcast to external UI websocket clients
    message = {"symbol": SYMBOL, "price": price, "timestamp": timestamp}
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            pass

async def on_ws_error(e: Exception):
    logger.error(f"WebSocket Client Error: {e}")

@app.on_event("startup")
async def startup_event():
    # Initialize infrastructure
    await redis_pub.connect()
    
    # Pre-load historical candles for technical indicator continuity
    await aggregator.load_historical_candles()
    
    # Start Finnhub WebSocket connection in background task
    global ws_client
    ws_client = FinnhubWSClient(symbol=SYMBOL, callback=on_tick, error_callback=on_ws_error)
    asyncio.create_task(ws_client.connect())
    logger.info("Data Ingestion Service started")

@app.on_event("shutdown")
async def shutdown_event():
    if ws_client:
        await ws_client.stop()
    await redis_pub.close()
    logger.info("Data Ingestion Service stopped")

@app.get("/health/live")
async def liveness():
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness():
    # Check dependencies
    redis_ok = redis_pub.connected
    ws_ok = ws_client and ws_client.is_running
    
    if redis_ok and ws_ok:
        return {"status": "ready"}
    return {"status": "not_ready", "redis": redis_ok, "ws": ws_ok}, 503

@app.get("/api/v1/price")
async def get_latest_price():
    # Return latest known price from aggregator's current M1 candle
    active_m1 = aggregator.current_candles.get("M1")
    if active_m1:
        return {"symbol": SYMBOL, "price": active_m1["close"], "timestamp": active_m1["timestamp"]}
    return {"error": "No price data available"}

@app.get("/api/v1/candles")
async def get_candles(timeframe: str = "M5", limit: int = 100):
    candles = aggregator.historical_candles.get(timeframe, [])
    
    # Include currently forming active candle
    active = aggregator.current_candles.get(timeframe)
    if active:
        response_candles = candles + [active]
    else:
        response_candles = candles
        
    return {
        "symbol": SYMBOL,
        "timeframe": timeframe,
        "candles": response_candles[-limit:]
    }

@app.websocket("/ws/price")
async def websocket_price(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Keep connection open, client might send heartbeats
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
