# Data Ingestion Service

The Data Ingestion Service is a robust Python FastAPI microservice responsible for collecting real-time XAU/USD trading data from the Finnhub WebSocket API, computing continuous candlestick aggregates (OHLCV), calculating technical indicators via Pandas-TA, and persisting everything to MongoDB and Redis for downstream usage.

## Architecture
1. **WebSocket Client**: Connects to `wss://ws.finnhub.io`, subscribes to `OANDA:XAU_USD` with auto-reconnect support.
2. **Candle Aggregator**: Collects rapid ticks and converts them into M1, M5, M15, M30, and 1H candles seamlessly.
3. **Indicator Engine**: Enhances completed candles with technical analysis metrics (RSI, MACD, Bollinger Bands, EMA, ADX).
4. **Data Persistence**: Uses Motor (Asyncio MongoDB) to flush raw ticks and fully formed candles to Time-Series optimized tables.
5. **Realtime Pub/Sub**: Pushes every new tick and completed candle to Redis channels `price:updates` and `candles:{tf}`.
6. **FastAPI**: Serves REST and WS routes for frontend querying.

## Setup Requirements

Environment variables needed (`.env` file):
```bash
FINNHUB_API_KEY="your-finnhub-key"
MONGODB_URI="mongodb://localhost:27017/trading"
REDIS_URL="redis://localhost:6379"
SYMBOL="OANDA:XAU_USD"
```

## Running Locally

### 1. Using Docker
```bash
docker build -t xau-data-ingest .
docker run --env-file .env -p 8080:8080 xau-data-ingest
```

### 2. Without Docker
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## API Endpoints

- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe (checks DB/Redis/WS connectivity)
- `GET /api/v1/price` - Returns the absolute latest tick price
- `GET /api/v1/candles?timeframe=M5&limit=100` - Returns a historical list of aggregated OHLCV candles with indicators attached
- `WS /ws/price` - Real-time WebSocket feed for frontend clients

## Testing
```bash
pytest tests/
```
