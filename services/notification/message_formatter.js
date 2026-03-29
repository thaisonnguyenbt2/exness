export class MessageFormatter {
  /**
   * Translates a JSON signal into an aesthetic Telegram message.
   * Uses HTML/MarkdownV2 compatible formatting logic.
   */
  static formatSignal(signal) {
    const isBuy = signal.type.toUpperCase() === 'BUY';
    const isUpdate = signal.type.toUpperCase() === 'UPDATE';
    
    let icon = '🔴';
    const dt = new Date(signal.timestamp);
    const options = { timeZone: 'Asia/Ho_Chi_Minh', hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    const timeStr = new Intl.DateTimeFormat('en-GB', options).format(dt).replace(',', '') + ' VNT';
    
    // Explicit bypass handler for instantaneous anomalies
    if (signal.type === "SHARK" || signal.type === "HIGHLIGHT") {
        return `━━━━━━━━━━━━━━━━━━━━\n${signal.message}\n\n⏰ ${timeStr}`;
    }
    
    // Aesthetic SMC Alert Interpolation
    if (signal.type === "SMC_ALERT" && signal.smc_data) {
        let smcHeader = "";
        let desc = "";
        if (signal.scenario === "SCENARIO_A") {
            smcHeader = "🔄 BẮT ĐỈNH/ĐÁY (ChoCh + FVG)";
            desc = "Xu hướng có dấu hiệu đảo chiều cực mạnh (Change of Character) kèm theo bứt phá để lại cấu trúc FVG.";
        } else if (signal.scenario === "SCENARIO_B") {
            smcHeader = "✅ TIẾP DIỄN XU HƯỚNG (BOS)";
            desc = "Cấu trúc phá vỡ đỉnh/đáy cũ, vược mặt kháng cự (Break of Structure). Xu hướng đang rất khỏe.";
        } else if (signal.scenario === "SCENARIO_C") {
            smcHeader = "🪤 BẪY THANH KHOẢN (Liquidity Sweep)";
            desc = "Tạo Lập (Market Maker) vừa quét râu Stoploss rồi lập tức rút chân. Cảnh giác cú lừa (Fake-out) đảo chiều!";
        }
        
        let message = `━━━━━━━━━━━━━━━━━━━━\n`;
        message += `🚀 <b>[${signal.symbol}] TÍN HIỆU SMC (Sniper)</b>\n`;
        message += `💥 <b>${smcHeader}</b>\n`;
        message += `<i>${desc}</i>\n\n`;
        
        message += `🏛 <b>Cấu trúc M5:</b> ${signal.smc_data.structure_m5} (M15: ${signal.smc_data.structure_m15})\n`;
        message += `📏 <b>Hợp lưu Đa khung (HTF):</b> ${signal.smc_data.htf_alignment ? "🟢 Đồng thuận" : "🔴 Đánh ngược"}\n`;
        message += `🧲 <b>Quét Phái sinh (Sweep):</b> ${signal.smc_data.sweep_detected ? "🟥 CÓ (Trap)" : "🟩 KHÔNG"}\n`;
        message += `⚡ <b>Lực bứt phá (FVG):</b> ${signal.smc_data.fvg_present ? "✅ Lực Đẩy Mạnh" : "❌ Di chuyển chậm"}\n`;
        
        if (signal.smc_data.poi_zone) {
            message += `🎯 <b>Điểm vào tối ưu (POI/OB):</b> $${signal.smc_data.poi_zone.toFixed(2)}\n`;
        }
        
        if (signal.liquidity_zones && Object.keys(signal.liquidity_zones).length > 0) {
            message += `\n📊 <b>CẤU TRÚC THANH KHOẢN LÂN CẬN:</b>\n`;
            for (const [tf, z] of Object.entries(signal.liquidity_zones)) {
                if (z.bfvg) message += `  🟢 FVG Mua (${tf}): ${z.bfvg}\n`;
                if (z.sfvg) message += `  🔴 FVG Bán (${tf}): ${z.sfvg}\n`;
            }
        }
        
        if (signal.ai_analysis) {
            const safeReasoning = signal.ai_analysis.reasoning.replace(/\\*/g, '');
            message += `\n🤖 <b>KHUYẾN NGHỊ:</b>\n${safeReasoning}\n\n`;
        }
        
        message += `⏰ ${timeStr}`;
        return message;
    }
    
    // Header structurally removed per user requirements
    let message = `━━━━━━━━━━━━━━━━━━━━\n`;
    
    const trendClean = signal.ai_analysis && signal.ai_analysis.trend ? signal.ai_analysis.trend.toUpperCase() : 'ĐI NGANG';
    const currentPrc = signal.entry_price > 0 ? `$${signal.entry_price.toFixed(2)}` : 'Đang tổng hợp...';
    
    // Dynamic Translation
    let phaseVn = "ĐI NGANG (Tích lũy)";
    if (trendClean === "BULLISH") phaseVn = "TĂNG (Bullish)";
    else if (trendClean === "BEARISH") phaseVn = "GIẢM (Bearish)";

    message += `📈 <b>Giai đoạn (15m):</b> ${phaseVn}\n`;
    message += `💰 <b>Giá hiện tại:</b> ${currentPrc}\n\n`;
    
    if (signal.stats) {
        message += `📊 <b>CHỈ BÁO KỸ THUẬT (Chuẩn MT5):</b>\n`;
        message += `• RSI (14): ${signal.stats.rsi}\n`;
        message += `• BB (20, 2): Hẹp [${signal.stats.bb_lower} - ${signal.stats.bb_upper}]\n`;
        message += `• MACD (12,26,9): Value: ${signal.stats.macd_val} | Sig: ${signal.stats.macd_signal}\n\n`;
    }
    
    // Deep structural mapping
    if (signal.liquidity_zones && Object.keys(signal.liquidity_zones).length > 0) {
        message += `🎯 <b>CẤU TRÚC THANH KHOẢN:</b>\n`;
        for (const [tf, z] of Object.entries(signal.liquidity_zones)) {
            // Check if it's the old string format (fallback for pending old signals)
            if (typeof z === 'string') {
                message += `• <b>${tf}:</b> ${z}\n`;
            } else {
                message += `\n⏱ <b>KHUNG ${tf}</b>:\n`;
                if (z.bfvg) message += `  🟢 FVG Mua: ${z.bfvg}\n`;
                if (z.sfvg) message += `  🔴 FVG Bán: ${z.sfvg}\n`;
                if (!z.bfvg && !z.sfvg) message += `  ⚠️ Trống thanh khoản (Chờ phá vỡ)\n`;
                message += `  ↕️ Vùng giá: ${z.sup} (Đáy) ➔ ${z.res} (Đỉnh)\n`;
            }
        }
        message += `\n`;
    }

    if (signal.highlight && signal.highlight.trim().length > 0) {
        message += `${signal.highlight}\n\n`;
    }
    
    if (signal.ai_analysis) {
        const safeReasoning = signal.ai_analysis.reasoning.replace(/\\*/g, '');
        message += `🤖 <b>CHIẾN LƯỢC GIAO DỊCH 15 PHÚT TỚI:</b>\n`;
        message += `${safeReasoning}\n\n`;
    }
    
    message += `⏰ ${timeStr}`;
    return message;
  }
}
