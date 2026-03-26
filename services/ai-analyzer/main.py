import asyncio
import logging
from fastapi import FastAPI
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

@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Analyzer Service")
    await signal_generator.connect()
    asyncio.create_task(signal_generator.start_listening())
    
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
