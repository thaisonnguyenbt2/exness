import { MongoClient } from 'mongodb';
import "dotenv/config";

export class Database {
  constructor() {
    this.uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/trading';
    this.client = new MongoClient(this.uri);
    this.dbName = 'trading';
  }

  async connect() {
    try {
      await this.client.connect();
      this.db = this.client.db(this.dbName);
      console.log('✅ Connected to MongoDB');
    } catch (error) {
      console.error('❌ MongoDB Connection Error:', error);
    }
  }

  async logDeliveryStatus(signalId, status, details = {}) {
    if (!this.db) return;

    try {
      await this.db.collection('signals').updateOne(
        { _id: signalId },
        {
          $set: {
            notification_status: status,
            notified_at: new Date(),
            ...details
          }
        }
      );
    } catch (error) {
      console.error('❌ Error logging delivery status:', error);
    }
  }

  async close() {
    await this.client.close();
  }
}
