from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager
from paper_trading import start_engine
from db import db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch the paper trading redis listener
    await start_engine()
    yield
    # Shutdown logic

app = FastAPI(title="Orchestrator Service", lifespan=lifespan)

@app.get("/api/v1/config")
async def get_config():
    return await db.get_system_config()

@app.get("/api/v1/trades")
async def get_trades(limit: int = 50):
    cursor = db.db.paper_trades.find().sort("created_at", -1).limit(limit)
    trades = await cursor.to_list(length=limit)
    for t in trades:
        t["_id"] = str(t["_id"])
    return {"trades": trades}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8082, reload=True)
