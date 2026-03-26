import os
from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta, timezone
import pymongo

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/trading")

app = Celery('trading_tasks', broker=REDIS_URL, backend=REDIS_URL)

app.conf.beat_schedule = {
    'daily-performance-report': {
        'task': 'celery_tasks.generate_daily_report',
        'schedule': crontab(hour=0, minute=0), # Midnight every day
    },
    'mongodb-cleanup': {
        'task': 'celery_tasks.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0), # 2 AM every day
    },
}

@app.task
def generate_daily_report():
    print("📊 Generating Daily Performance Report...")
    # Logic to aggregate trades from MongoDB and compute daily P/L
    # Could be published back to Telegram via Redis
    pass

@app.task
def cleanup_old_data():
    print("🧹 Cleaning up old tick data from MongoDB (>7 days)...")
    client = pymongo.MongoClient(MONGODB_URI)
    db = client.trading
    
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    
    # Example cleanup of the raw ticks collection
    result = db.ticks.delete_many({"timestamp": {"$lt": seven_days_ago}})
    print(f"✅ Deleted {result.deleted_count} old ticks.")
    
    # Similarly clean up old M1 candles
    result = db.candles.delete_many({"timeframe": "M1", "timestamp": {"$lt": seven_days_ago}})
    print(f"✅ Deleted {result.deleted_count} old M1 candles.")
