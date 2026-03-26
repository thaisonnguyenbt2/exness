import Redis from 'ioredis';
import "dotenv/config";

export class RateLimiter {
  constructor() {
    this.redisUrl = process.env.REDIS_URL || 'redis://localhost:6379';
    this.redis = new Redis(this.redisUrl);
    // Max 1 notification per 5 minutes (300 seconds)
    this.cooldownSeconds = 300; 
  }

  /**
   * Checks if a user/chat is allowed to receive a notification for this symbol.
   * Returns true if allowed, false if rate limited.
   */
  async checkRateLimit(chatId, symbol) {
    const key = `ratelimit:${chatId}:${symbol}`;
    
    // Check if key exists
    const exists = await this.redis.exists(key);
    if (exists) {
      return false; // Rate limited!
    }
    
    // Set the ratelimit key with an expiration of 5 minutes
    await this.redis.set(key, '1', 'EX', this.cooldownSeconds);
    return true; // Allowed
  }
}
