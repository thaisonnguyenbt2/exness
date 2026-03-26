export class MessageFormatter {
  /**
   * Translates a JSON signal into an aesthetic Telegram message.
   * Uses HTML/MarkdownV2 compatible formatting logic.
   */
  static formatSignal(signal) {
    const isBuy = signal.type.toUpperCase() === 'BUY';
    const icon = isBuy ? '🟢' : '🔴';
    const title = `${icon} **${signal.type.toUpperCase()} SIGNAL - ${signal.symbol}**`;
    
    // Calculate P/L diffs
    const stopLossDiff = (signal.stop_loss - signal.entry_price).toFixed(2);
    const takeProfitDiff = (signal.take_profit - signal.entry_price).toFixed(2);
    const stopLossSign = stopLossDiff > 0 ? '+' : '';
    const takeProfitSign = takeProfitDiff > 0 ? '+' : '';

    const dt = new Date(signal.timestamp);
    const timeStr = dt.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
    
    let message = `${title}\n`;
    message += `━━━━━━━━━━━━━━━━━━━━\n`;
    message += `📊 **Confidence:** ${signal.confidence}%\n`;
    message += `💰 **Entry:** $${signal.entry_price}\n`;
    message += `🛑 **Stop Loss:** $${signal.stop_loss} (${stopLossSign}$${stopLossDiff})\n`;
    message += `🎯 **Take Profit:** $${signal.take_profit} (${takeProfitSign}$${takeProfitDiff})\n\n`;
    
    if (signal.ai_analysis) {
        message += `🤖 **AI Analysis:**\n`;
        message += `${signal.ai_analysis.reasoning}\n\n`;
    }
    
    message += `⏰ ${timeStr}`;
    
    return message;
  }
}
