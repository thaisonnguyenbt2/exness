# Trading Orchestrator Service

The orchestrator sits above all data pipelines and manages system health, configuration states, and mock P/L simulations. 

## Features
- **Paper Trading Engine**: Listens to Redis for `signals:new`, writes them as virtual `OPEN` trades to MongoDB, and continuously listens to `price:updates` to determine if entry price hits virtual Stop Limits or Take Profits, resulting in a perfectly isolated Paper Trading P/L Ledger without risking real capital.
- **REST API**: Serves up the generated Paper Trade ledger directly back to the Next.js frontend via `/api/v1/trades`.
- **Celery Schedulers**: Deletes bloated M1 ticks/candles older than 7 days using robust crontab schedules dynamically stored in Redis.

## Deployment
This service requires **Three** unique micro-containers scaling from the single compiled image:
1. `uvicorn main:app` (The FastAPI REST Server + Ledger tracking thread)
2. `celery -A celery_tasks worker --loglevel=info` (The Celery worker pool)
3. `celery -A celery_tasks beat --loglevel=info` (The Celery scheduler loop orchestrating crontabs)
