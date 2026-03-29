import axios from 'axios';
import "dotenv/config";

export class TelegramClient {
  constructor() {
    this.token = process.env.TELEGRAM_BOT_TOKEN;
    // You can supply a specific chat ID, or broadcasting to a channel
    this.chatId = process.env.TELEGRAM_CHAT_ID; 
    
    if (!this.token || !this.chatId) {
       console.warn("⚠️ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing. Notifications will bounce.");
    }
    this.baseUrl = `https://api.telegram.org/bot${this.token}`;
  }

  async sendMessage(text) {
    if (!this.token || !this.chatId) return false;

    try {
      const response = await axios.post(`${this.baseUrl}/sendMessage`, {
        chat_id: this.chatId,
        text: text,
        parse_mode: 'HTML'
      });
      return response.data.ok;
    } catch (error) {
      console.error("❌ Telegram API Error:", error.response?.data || error.message);
      return false;
    }
  }
}
