import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from db import DatabaseSchema
from signal_generator import SignalGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ai-analyzer")

app = FastAPI(title="XAU/USD AI Analyzer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseSchema()
signal_generator = SignalGenerator(db)
active_ws_connections: list[WebSocket] = []

async def redis_to_ws_broadcaster():
    """Listens to analysis:live and broadcasts to all connected WebSockets."""
    try:
        pubsub = signal_generator.redis_client.pubsub()
        await pubsub.subscribe("analysis:live")
        logger.info("WebSocket broadcaster subscribing to analysis:live")
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                for connection in active_ws_connections.copy():
                    try:
                        await connection.send_text(data)
                    except Exception:
                        if connection in active_ws_connections:
                            active_ws_connections.remove(connection)
    except Exception as e:
        logger.error(f"Broadcaster error: {e}")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Analyzer Service")
    await signal_generator.connect()
    asyncio.create_task(signal_generator.start_listening())
    asyncio.create_task(redis_to_ws_broadcaster())
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping AI Analyzer Service")
    await signal_generator.close()
    await db.close()

@app.get("/health/live")
async def liveness():
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness():
    db_ok = db.client is not None
    if db_ok:
        return {"status": "ready"}
    return {"status": "not_ready"}, 503

@app.get("/api/v1/signals")
async def get_signals(limit: int = 10):
    """Retrieve recent AI trading signals."""
    try:
        cursor = db.db.signals.find().sort("timestamp", -1).limit(limit)
        signals = await cursor.to_list(limit)
        for s in signals:
            s["id"] = str(s.pop('_id'))
        return {"signals": signals}
    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        return {"error": str(e)}

@app.websocket("/ws/analysis")
async def websocket_analysis(websocket: WebSocket):
    await websocket.accept()
    active_ws_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_ws_connections:
            active_ws_connections.remove(websocket)
