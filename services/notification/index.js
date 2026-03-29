import Redis from 'ioredis';
import { TelegramClient } from './telegram.js';
import { MessageFormatter } from './message_formatter.js';
import { RateLimiter } from './rate_limiter.js';
import { Database } from './db.js';
import "dotenv/config";

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const pubsub = new Redis(REDIS_URL, { enableReadyCheck: false });
const telegram = new TelegramClient();
const rateLimiter = new RateLimiter();
const db = new Database();

// Prevent ioredis unhandled exception crashes
pubsub.on('error', (err) => {
    // Ignore harmless subscriber mode sync errors
    if (!err.message.includes('subscriber mode')) {
        console.error('Redis error:', err);
    }
});

async function start() {
  console.log("🚀 Starting Notification Service...");
  
  await db.connect();

  pubsub.subscribe('signals:new', (err, count) => {
    if (err) {
      console.error('❌ Failed to subscribe:', err.message);
    } else {
      console.log(`✅ Subscribed to Redis channels: ${count}`);
    }
  });

  pubsub.on('message', async (channel, message) => {
    if (channel === 'signals:new') {
      try {
        const signal = JSON.parse(message);
        console.log(`🔔 Received signal: ${signal.type} for ${signal.symbol}`);
        
        // Use global chat id configured in ENV
        const chatId = process.env.TELEGRAM_CHAT_ID;
        if (!chatId) {
          console.warn("Skip: TELEGRAM_CHAT_ID not provided.");
          return;
        }

        // 1. Rate Limiting Check (Bypass for anomalies since Python natively limits them)
        if (signal.type !== "SHARK" && signal.type !== "HIGHLIGHT" && signal.type !== "SMC_ALERT") {
            const allowed = await rateLimiter.checkRateLimit(chatId, signal.symbol);
            if (!allowed) {
              console.log(`⌛ Rate limited: Skipping standard alert for ${signal.symbol}`);
              if (signal.id) await db.logDeliveryStatus(signal.id, 'rate_limited');
              return;
            }
        }

        // 1.5. Night-time Silence Mode (23:00 - 06:00 VNT)
        if (signal.type === "HIGHLIGHT" || signal.type === "UPDATE") {
            const vntDate = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Ho_Chi_Minh" }));
            const currentHour = vntDate.getHours();
            
            // Sleep window: 11 PM to 6 AM Vietnam Time
            if (currentHour >= 23 || currentHour < 6) {
                console.log(`🌙 Night-mode active: Muting non-critical ${signal.type} for ${signal.symbol}`);
                if (signal.id) await db.logDeliveryStatus(signal.id, 'muted_night_mode');
                return;
            }
        }

        // 2. Format Message
        const text = MessageFormatter.formatSignal(signal);

        // 3. Send Telegram Alert
        const success = await telegram.sendMessage(text);

        // 4. Log Status in MongoDB
        if (success) {
          console.log(`✈️ Successfully sent Telegram alert for ${signal.symbol}`);
          await db.logDeliveryStatus(signal.id, 'sent');
        } else {
          console.error(`❌ Failed to send Telegram alert for ${signal.symbol}`);
          await db.logDeliveryStatus(signal.id, 'failed', { error: 'Telegram API rejected' });
        }

      } catch (error) {
        console.error('❌ Error processing signal:', error);
      }
    }
  });
}

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log("Shutting down...");
    pubsub.disconnect();
    await db.close();
    process.exit(0);
});

start();
