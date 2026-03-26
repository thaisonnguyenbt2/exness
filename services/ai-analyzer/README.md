# AI Analyzer Service

The AI Analyzer Service subscribes to real-time `price:updates` from the Data Ingestion service and evaluates gold (XAU/USD) market trends using Google's Gemini Models.

## Architecture
1. **Redis Subscriber**: Listens for fresh price ticks coming from the primary ingestion pipeline.
2. **Signal Generator**: Throttles analysis (max 1 per 30s) and triggers a prompt generation using the last 100 aggregated candles.
3. **Gemini Analyzer**: Uses `gemini-1.5-flash` to evaluate RSI, MACD, BB, EMA, ADX and recent price action. Instructed to emit strict structured JSON with signal confidence.
4. **Signal Publisher**: If the confidence exceeds 70%, the signal is recorded in MongoDB and pushed to Redis (`signals:new`) for the Notification service.

## Environment Variables
```bash
GEMINI_API_KEY="AIzaSy..."
MONGODB_URI="mongodb://localhost:27017/trading"
REDIS_URL="redis://localhost:6379"
```

## Running
```bash
docker build -t xau-ai-analyzer .
docker run --env-file .env -p 8081:8080 xau-ai-analyzer
```
