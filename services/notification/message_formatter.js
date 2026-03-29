export class MessageFormatter {
  /**
   * Format any signal or trade lifecycle event into a Telegram message.
   * Rule: price / action FIRST, explanation BELOW.
   */

  // ── Trade lifecycle (new) ─────────────────────────────────────────────

  static formatPreOrder(event) {
    const dir    = event.direction === 'BUY' ? '🟢 BUY' : '🔴 SELL';
    const dirEmj = event.direction === 'BUY' ? '📈' : '📉';
    const ts     = MessageFormatter._time(event.timestamp);
    const s      = event.stats  || {};
    const smc    = event.smc_data || {};

    // ── Header: price + action ───────────────────────────────────
    let msg = `━━━━━━━━━━━━━━━━━━━━\n`;
    msg += `${dir} <b>@ $${event.entry.toFixed(2)}</b>\n`;
    msg += `🎯 SL: <b>$${event.stop.toFixed(2)}</b> (-$10)   TP: <b>$${event.tp.toFixed(2)}</b> (+$10)\n`;
    msg += `<i>Pre-order placed — awaiting fill confirmation</i>\n\n`;

    // ── Why this trade? ─────────────────────────────────────────
    msg += `${dirEmj} <b>Why this trade?</b>\n`;

    // Trend context
    if (event.trend) {
      const trendLabel = event.trend === 'bullish' ? '🟢 Bullish' : event.trend === 'bearish' ? '🔴 Bearish' : '⬛ Ranging';
      msg += `• Market Trend: ${trendLabel}\n`;
    }

    // Indicator interpretation
    if (s.rsi) {
      let rsiNote = '';
      if (s.rsi < 30)       rsiNote = ' → Oversold, reversal likely';
      else if (s.rsi > 70)  rsiNote = ' → Overbought, caution on longs';
      else if (s.rsi < 45)  rsiNote = ' → Weak momentum, bearish lean';
      else if (s.rsi > 55)  rsiNote = ' → Strong momentum, bullish lean';
      else                   rsiNote = ' → Neutral zone';
      msg += `• RSI (14): ${s.rsi}${rsiNote}\n`;
    }
    if (s.ma20 && s.ma50) {
      const maTrend = s.ma20 > s.ma50
        ? `MA20 (${s.ma20}) > MA50 (${s.ma50}) → Short-term bullish bias`
        : `MA20 (${s.ma20}) < MA50 (${s.ma50}) → Short-term bearish bias`;
      msg += `• Moving Averages: ${maTrend}\n`;
    }
    if (s.bb_lower && s.bb_upper && event.entry) {
      const bbMid  = +s.bb_middle || ((+s.bb_lower + +s.bb_upper) / 2);
      const bbPos  = event.entry > bbMid ? 'upper half (bearish extension)' : 'lower half (support zone)';
      msg += `• Bollinger Bands: Price in ${bbPos} [${s.bb_lower}–${s.bb_upper}]\n`;
    }
    if (s.macd_val !== undefined) {
      const macdCross = s.macd_val > s.macd_signal ? 'bullish cross' : 'bearish cross';
      msg += `• MACD: ${s.macd_val} vs Signal ${s.macd_signal} → ${macdCross}\n`;
    }

    // SMC context
    if (smc.structure_m15 || smc.structure_m5) {
      msg += `• Structure: M15 ${smc.structure_m15 || '–'} / M5 ${smc.structure_m5 || '–'}\n`;
    }
    if (smc.sweep_detected) msg += `• 🧲 Liquidity swept — strong reversal signal\n`;
    if (smc.choch)          msg += `• 🔄 ChoCh detected — momentum shift confirmed\n`;
    if (smc.bos)            msg += `• ✅ BOS confirmed — continuation bias\n`;
    if (smc.fvg_present)    msg += `• ⚡ FVG open — price likely rebalancing\n`;
    if (smc.poi_zone)       msg += `• 🎯 Key POI/OB: $${parseFloat(smc.poi_zone).toFixed(2)}\n`;

    // Scenario label
    if (event.scenario) {
      msg += `• 📐 Setup: ${MessageFormatter._scenario(event.scenario)}\n`;
    }

    // Textual reasoning from the engine
    const reasoning = event.reasoning || event.ai_analysis?.reasoning || '';
    if (reasoning) {
      msg += `\n💬 <i>${reasoning}</i>\n`;
    }

    // ── Position details ─────────────────────────────────────────
    msg += `\n⚖️ <b>Position</b>\n`;
    msg += `• Risk: $${event.risk.toFixed(2)} (2% of $${event.budget})   Reward: +$${(event.risk * 2).toFixed(2)}\n`;
    msg += `• Qty: ${event.qty} contracts   Confidence: ${event.confidence || '–'}%\n`;

    msg += `\n⏰ ${ts}`;
    return msg;
  }


  static formatFilled(event) {
    const dir = event.direction === 'BUY' ? '🟢 BUY' : '🔴 SELL';
    const ts  = MessageFormatter._time(event.timestamp);

    let msg = `━━━━━━━━━━━━━━━━━━━━\n`;
    msg += `✅ ORDER FILLED — ${dir} <b>@ $${event.entry.toFixed(2)}</b>\n\n`;
    msg += `• Symbol: ${event.symbol}\n`;
    msg += `• Qty: ${event.qty} contracts\n`;
    msg += `• Stop-Loss: $${event.stop.toFixed(2)}\n`;
    msg += `• Take-Profit: $${event.tp.toFixed(2)}\n`;
    msg += `• Risk: $${event.risk.toFixed(2)}\n\n`;
    msg += `<i>Monitoring the position — alerts when TP or SL is hit.</i>\n\n`;
    msg += `⏰ ${ts}`;
    return msg;
  }

  static formatClosed(event) {
    const ts      = MessageFormatter._time(event.timestamp);
    const pnl     = event.pnl;
    const isWin   = event.outcome === 'TP';
    const header  = isWin
      ? `🏆 TAKE-PROFIT HIT — SELL @ <b>$${event.exit_price.toFixed(2)}</b>`
      : `❌ STOP-LOSS HIT — SELL @ <b>$${event.exit_price.toFixed(2)}</b>`;

    let msg = `━━━━━━━━━━━━━━━━━━━━\n`;
    msg += `${header}\n`;
    msg += `<b>Result: ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</b>\n\n`;

    msg += `📋 <b>Trade Summary</b>\n`;
    msg += `• Symbol: ${event.symbol}\n`;
    msg += `• Direction: ${event.direction}\n`;
    msg += `• Entry: $${event.entry.toFixed(2)}  →  Exit: $${event.exit_price.toFixed(2)}\n`;
    msg += `• Qty: ${event.qty} contracts\n`;
    msg += `• Risked: $${event.risk.toFixed(2)}\n`;
    msg += `• P&L: ${pnl >= 0 ? '🟢' : '🔴'} ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}\n`;
    msg += `• Budget after trade: $${event.budget_after.toFixed(2)}\n\n`;

    if (isWin) {
      msg += `<i>Structural SMC edge confirmed. Price respected the POI and delivered the 1:2 reward.</i>\n\n`;
    } else {
      msg += `<i>Structure invalidated. Risk was contained to $${event.risk.toFixed(2)} (2% rule preserved capital).</i>\n\n`;
    }
    msg += `⏰ ${ts}`;
    return msg;
  }

  // ── 15-minute market update ─────────────────────────────────────────────

  static formatMarketUpdate(signal) {
    const ts    = MessageFormatter._time(signal.timestamp);
    const price = signal.price ? `$${parseFloat(signal.price).toFixed(2)}` : 'N/A';
    const trend = (signal.trend || 'ranging').toUpperCase();
    const trendIcon = trend === 'BULLISH' ? '📈 BULLISH ↑'
                    : trend === 'BEARISH' ? '📉 BEARISH ↓'
                    : '➡️  SIDEWAYS';

    let msg = `━━━━━━━━━━━━━━━━━━━━\n`;
    msg += `📊 <b>${signal.symbol} — 15m Market Update</b>\n`;
    msg += `💰 <b>Price: ${price}</b>     Trend: ${trendIcon}\n\n`;

    // Market structure
    msg += `🏛 <b>Structure</b>\n`;
    msg += `• M5:  ${signal.structure_m5 || 'N/A'}\n`;
    msg += `• M15: ${signal.structure_m15 || 'N/A'}\n`;
    msg += `• HTF Alignment: ${signal.htf_alignment ? '🟢 Confirmed' : '🔴 Against'}\n\n`;

    // Active SMC conditions
    const flags = [];
    if (signal.sweep) flags.push('🧲 Liquidity Sweep active');
    if (signal.bos)   flags.push('✅ BOS confirmed');
    if (signal.choch) flags.push('🔄 ChoCh detected');
    if (signal.fvg)   flags.push('⚡ FVG / Imbalance present');
    if (flags.length) {
      msg += `⚡ <b>Active Signals</b>\n`;
      flags.forEach(f => { msg += `• ${f}\n`; });
      msg += `\n`;
    }

    // Key indicators
    if (signal.stats && Object.keys(signal.stats).length) {
      const s = signal.stats;
      msg += `📐 <b>Indicators</b>\n`;
      if (s.rsi)          msg += `• RSI (14): ${s.rsi}\n`;
      if (s.macd_val)     msg += `• MACD: ${s.macd_val} | Signal: ${s.macd_signal}\n`;
      if (s.bb_lower)     msg += `• BB (20,2): [${s.bb_lower} – ${s.bb_upper}]\n`;
      msg += `\n`;
    }

    // Upcoming possibilities
    if (signal.outlook && signal.outlook.length) {
      msg += `🔮 <b>What's Coming Next</b>\n`;
      signal.outlook.forEach(line => { msg += `${line}\n`; });
      msg += `\n`;
    }

    // AI reasoning (truncated to keep message concise)
    if (signal.reasoning && signal.reasoning.trim()) {
      const clean = signal.reasoning.replace(/\*+/g, '').trim();
      const short = clean.length > 400 ? clean.slice(0, 400) + '…' : clean;
      msg += `🤖 <b>Strategy Note</b>\n${short}\n\n`;
    }

    msg += `💼 <b>Active Budget:</b> $${signal.budget || 500}\n`;
    msg += `⏰ ${ts}`;
    return msg;
  }



  static formatSignal(signal) {
    // If this is a trade lifecycle event routed through signals:new, delegate
    if (signal.event === 'pre_order')    return MessageFormatter.formatPreOrder(signal);
    if (signal.event === 'filled')       return MessageFormatter.formatFilled(signal);
    if (signal.event === 'trade_closed') return MessageFormatter.formatClosed(signal);

    // 15-minute market update
    if (signal.type === 'UPDATE') return MessageFormatter.formatMarketUpdate(signal);


    // Normalise: analyzer publishes `signal` field, lifecycle uses `type`
    if (!signal.type && signal.signal) signal.type = signal.signal;
    // Ensure timestamp is always valid
    if (!signal.timestamp) signal.timestamp = Date.now();

    const isBuy    = signal.type && signal.type.toUpperCase() === 'BUY';
    const isUpdate = signal.type && signal.type.toUpperCase() === 'UPDATE';

    let icon = '🔴';
    const dt      = new Date(signal.timestamp);
    const options = { timeZone: 'Asia/Ho_Chi_Minh', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    const timeStr = new Intl.DateTimeFormat('en-GB', options).format(dt).replace(',', '') + ' VNT';

    if (signal.type === 'SHARK' || signal.type === 'HIGHLIGHT') {
      return `━━━━━━━━━━━━━━━━━━━━\n${signal.message}\n\n⏰ ${timeStr}`;
    }

    if (signal.type === 'SMC_ALERT' && signal.smc_data) {
      let smcHeader = '';
      let desc      = '';
      if (signal.scenario === 'SCENARIO_A') {
        smcHeader = '🔄 REVERSAL (ChoCh + FVG)';
        desc      = 'Change of Character detected — strong trend reversal signal with FVG imbalance.';
      } else if (signal.scenario === 'SCENARIO_B') {
        smcHeader = '✅ CONTINUATION (BOS)';
        desc      = 'Break of Structure confirmed — trend momentum continues aggressively.';
      } else if (signal.scenario === 'SCENARIO_C') {
        smcHeader = '🪤 LIQUIDITY TRAP (Sweep)';
        desc      = 'Market Maker swept stop-losses then reversed. Beware of the fake-out.';
      }

      let message = `━━━━━━━━━━━━━━━━━━━━\n`;
      message += `🚀 <b>[${signal.symbol}] SMC SIGNAL</b>\n`;
      message += `💥 <b>${smcHeader}</b>\n`;
      message += `<i>${desc}</i>\n\n`;
      message += `🏛 <b>Structure M5:</b> ${signal.smc_data.structure_m5} (M15: ${signal.smc_data.structure_m15})\n`;
      message += `📏 <b>HTF Alignment:</b> ${signal.smc_data.htf_alignment ? '🟢 Confirmed' : '🔴 Against'}\n`;
      message += `🧲 <b>Sweep:</b> ${signal.smc_data.sweep_detected ? '🟥 YES (Trap)' : '🟩 NO'}\n`;
      message += `⚡ <b>FVG:</b> ${signal.smc_data.fvg_present ? '✅ Present' : '❌ Absent'}\n`;
      if (signal.smc_data.poi_zone) {
        message += `🎯 <b>POI / OB:</b> $${parseFloat(signal.smc_data.poi_zone).toFixed(2)}\n`;
      }
      message += `\n⏰ ${timeStr}`;
      return message;
    }

    let message = `━━━━━━━━━━━━━━━━━━━━\n`;
    const trendClean = signal.ai_analysis && signal.ai_analysis.trend ? signal.ai_analysis.trend.toUpperCase() : 'SIDEWAYS';
    const currentPrc = signal.entry_price > 0 ? `$${signal.entry_price.toFixed(2)}` : 'Aggregating...';
    let phaseVn = 'SIDEWAYS (Accumulation)';
    if (trendClean === 'BULLISH') phaseVn = 'BULLISH ↑';
    else if (trendClean === 'BEARISH') phaseVn = 'BEARISH ↓';
    message += `📈 <b>Trend (15m):</b> ${phaseVn}\n`;
    message += `💰 <b>Price:</b> ${currentPrc}\n\n`;
    if (signal.stats) {
      message += `📊 <b>INDICATORS:</b>\n`;
      message += `• RSI (14): ${signal.stats.rsi}\n`;
      message += `• BB (20,2): [${signal.stats.bb_lower} – ${signal.stats.bb_upper}]\n`;
      message += `• MACD: ${signal.stats.macd_val} | Sig: ${signal.stats.macd_signal}\n\n`;
    }
    if (signal.ai_analysis) {
      const safeReasoning = signal.ai_analysis.reasoning.replace(/\\*/g, '');
      message += `🤖 <b>STRATEGY (next 15m):</b>\n${safeReasoning}\n\n`;
    }
    message += `⏰ ${timeStr}`;
    return message;
  }

  // ── private helpers ───────────────────────────────────────────────────

  static _time(iso) {
    const dt      = new Date(iso);
    const options = { timeZone: 'Asia/Ho_Chi_Minh', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    return new Intl.DateTimeFormat('en-GB', options).format(dt).replace(',', '') + ' VNT';
  }

  static _scenario(s) {
    if (s === 'SCENARIO_A') return 'Reversal (ChoCh + FVG)';
    if (s === 'SCENARIO_B') return 'Continuation (BOS)';
    if (s === 'SCENARIO_C') return 'Liquidity Trap (Sweep)';
    return s;
  }
}
