import Redis from 'ioredis';
import { TelegramClient } from './telegram.js';
import { MessageFormatter } from './message_formatter.js';
import { RateLimiter } from './rate_limiter.js';
import { Database } from './db.js';
import "dotenv/config";

const REDIS_URL  = process.env.REDIS_URL || 'redis://localhost:6379';
const pubsub     = new Redis(REDIS_URL, { enableReadyCheck: false });
const telegram   = new TelegramClient();
const rateLimiter = new RateLimiter();
const db          = new Database();

// Trade lifecycle channels (from paper_trading.py)
const TRADE_CHANNELS = ['trade:pre_order', 'trade:filled', 'trade:closed'];

pubsub.on('error', (err) => {
    if (!err.message.includes('subscriber mode')) {
        console.error('Redis error:', err);
    }
});

async function handleTradeEvent(channel, data) {
    let text;
    if (channel === 'trade:pre_order') {
        text = MessageFormatter.formatPreOrder(data);
    } else if (channel === 'trade:filled') {
        text = MessageFormatter.formatFilled(data);
    } else if (channel === 'trade:closed') {
        text = MessageFormatter.formatClosed(data);
    }
    if (!text) return;

    const success = await telegram.sendMessage(text);
    const label   = `[${channel}] ${data.symbol} ${data.direction || ''} @ ${data.entry || data.exit_price || ''}`;
    if (success) {
        console.log(`✈️  Telegram sent  ${label}`);
    } else {
        console.error(`❌ Telegram failed ${label}`);
    }
}

async function handleSignal(data) {
    const chatId = process.env.TELEGRAM_CHAT_ID;
    if (!chatId) { console.warn('Skip: TELEGRAM_CHAT_ID not set'); return; }

    // Rate-limit standard market signals only (not anomalies)
    if (data.type !== 'SHARK' && data.type !== 'HIGHLIGHT' && data.type !== 'SMC_ALERT') {
        const allowed = await rateLimiter.checkRateLimit(chatId, data.symbol);
        if (!allowed) {
            console.log(`⌛ Rate limited: ${data.symbol}`);
            if (data.id) await db.logDeliveryStatus(data.id, 'rate_limited');
            return;
        }
    }

    // Night-time silence (23:00–06:00 VNT) for non-critical signals
    if (data.type === 'HIGHLIGHT' || data.type === 'UPDATE') {
        const vnt  = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Ho_Chi_Minh' }));
        const hour = vnt.getHours();
        if (hour >= 23 || hour < 6) {
            console.log(`🌙 Night-mode: muting ${data.type}`);
            if (data.id) await db.logDeliveryStatus(data.id, 'muted_night_mode');
            return;
        }
    }

    const text    = MessageFormatter.formatSignal(data);
    const success = await telegram.sendMessage(text);
    if (success) {
        console.log(`✈️  Telegram sent  signals:new ${data.symbol}`);
        await db.logDeliveryStatus(data.id, 'sent');
    } else {
        console.error(`❌ Telegram failed signals:new ${data.symbol}`);
        await db.logDeliveryStatus(data.id, 'failed', { error: 'Telegram API rejected' });
    }
}

async function start() {
    console.log('🚀 Starting Notification Service...');
    await db.connect();

    // Subscribe to all channels
    const allChannels = ['signals:new', ...TRADE_CHANNELS];
    pubsub.subscribe(...allChannels, (err, count) => {
        if (err) {
            console.error('❌ Failed to subscribe:', err.message);
        } else {
            console.log(`✅ Subscribed to ${count} Redis channels: ${allChannels.join(', ')}`);
        }
    });

    pubsub.on('message', async (channel, message) => {
        try {
            const data = JSON.parse(message);

            if (TRADE_CHANNELS.includes(channel)) {
                await handleTradeEvent(channel, data);
            } else if (channel === 'signals:new') {
                console.log(`🔔 Signal: ${data.type} — ${data.symbol}`);
                await handleSignal(data);
            }
        } catch (err) {
            console.error(`❌ Error processing [${channel}]:`, err);
        }
    });
}

process.on('SIGINT', async () => {
    console.log('Shutting down...');
    pubsub.disconnect();
    await db.close();
    process.exit(0);
});

start();
