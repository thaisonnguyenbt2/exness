# Notification Service

The Notification Service acts as the final step in the backend signals pipeline. It subscribes to Redis for freshly analyzed `BUY` or `SELL` signals and broadcasts them as beautifully stylized Telegram alerts to end users or groups.

## Features
- **Redis PubSub**: Immediately captures AI Analyzer signals.
- **Rich Formatting**: Converts raw JSON signals into clean, readable Markdown (with emoji indicators, entry points, stops, and P/L).
- **Rate-Limiting**: Uses `ioredis` to enforce a strictly 1 alert per 5 minutes rule *per symbol* to prevent indicator flapping/spam during high-volatility events.
- **MongoDB Delivery Receipts**: Every broadcast attempt is logged to the `signals` collection marking `sent`, `rate_limited`, or `failed`.

## Environment Variables
Create a `.env` file in this directory:
```bash
TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
TELEGRAM_CHAT_ID="your_target_chat_id"
MONGODB_URI="mongodb://localhost:27017/trading"
REDIS_URL="redis://localhost:6379"
```

## Running Locally

### 1. Using NPM natively
```bash
# Requires Node.js 20+
npm install
npm start
```

### 2. Using Docker
```bash
docker build -t xau-notification .
docker run --env-file .env xau-notification
```
