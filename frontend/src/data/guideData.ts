export interface GuideItem {
  id: string;
  name: string;
  category: "Trend" | "Momentum" | "Volatility" | "Volume" | "Support/Resistance";
  formula: string;
  description: string;
  recommended_value: string;
  signal_meaning: {
    bullish: string;
    bearish: string;
  };
}

export const GUIDE_DATA: GuideItem[] = [
  {
    id: "ema",
    name: "EMA (Exponential Moving Average)",
    category: "Trend",
    formula: "EMA = Price(t) * k + EMA(y) * (1 - k)",
    description: "เส้นค่าเฉลี่ยเคลื่อนที่แบบถ่วงน้ำหนักความสำคัญกับราคาล่าสุดมากกว่าราคาในอดีต ช่วยให้เห็นแนวโน้มของราคาง่ายขึ้น",
    recommended_value: "50 วัน (ระยะกลาง), 200 วัน (ระยะยาว)",
    signal_meaning: {
      bullish: "ราคาอยู่เหนือเส้น EMA หรือเส้นสั้นตัดเส้นยาวขึ้น (Golden Cross)",
      bearish: "ราคาอยู่ใต้เส้น EMA หรือเส้นสั้นตัดเส้นยาวลง (Death Cross)"
    }
  },
  {
    id: "rsi",
    name: "RSI (Relative Strength Index)",
    category: "Momentum",
    formula: "RSI = 100 - [100 / (1 + RS)]",
    description: "ดัชนีวัดกำลังสัมพัทธ์ ใช้ดูความเร็วและแรงเหวี่ยงของราคา เพื่อหาภาวะการซื้อหรือขายที่มากเกินไป",
    recommended_value: "14 วัน (มาตรฐาน)",
    signal_meaning: {
      bullish: "RSI < 30 (Oversold) มีโอกาสเด้งกลับ หรือตัดเส้น 50 ขึ้น",
      bearish: "RSI > 70 (Overbought) มีโอกาสปรับฐาน หรือตัดเส้น 50 ลง"
    }
  },
  {
    id: "macd",
    name: "MACD (Moving Average Convergence Divergence)",
    category: "Trend",
    formula: "MACD = EMA(12) - EMA(26)",
    description: "เครื่องมือวัดการรวมตัวและกระจายตัวของเส้นค่าเฉลี่ย ช่วยยืนยันแนวโน้มและความแรงของราคา",
    recommended_value: "12, 26, 9 (มาตรฐาน)",
    signal_meaning: {
      bullish: "เส้น MACD ตัดเส้น Signal ขึ้น หรืออยู่เหนือเส้น 0",
      bearish: "เส้น MACD ตัดเส้น Signal ลง หรืออยู่ใต้เส้น 0"
    }
  },
  {
    id: "bb",
    name: "Bollinger Bands",
    category: "Volatility",
    formula: "Upper/Lower = SMA(20) +/- (2 * StdDev)",
    description: "เครื่องมือวัดขอบเขตการเคลื่อนที่ของราคาตามความผันผวน ใช้ดูว่าราคาถูกหรือแพงเกินไปเทียบกับค่าเฉลี่ย",
    recommended_value: "Period 20, StdDev 2",
    signal_meaning: {
      bullish: "ราคาเริ่มเกาะเส้นขอบบน (Upper Band) หรือเด้งจากขอบล่าง",
      bearish: "ราคาเริ่มเกาะเส้นขอบล่าง (Lower Band) หรือหลุดขอบล่างลงไป"
    }
  },
  {
    id: "atr",
    name: "ATR (Average True Range)",
    category: "Volatility",
    formula: "ATR = Moving Average of True Range",
    description: "เครื่องมือวัดความผันผวนของราคา ไม่ได้บอกทิศทาง แต่บอกว่าหุ้นขยับแรงแค่ไหน",
    recommended_value: "14 วัน (ใช้คำนวณ Stop Loss)",
    signal_meaning: {
      bullish: "ความผันผวนเพิ่มขึ้นพร้อมทิศทางขาขึ้น (ยืนยันรอบใหม่)",
      bearish: "ความผันผวนเพิ่มขึ้นพร้อมทิศทางขาลง (ความเสี่ยงสูง)"
    }
  },
  {
    id: "adx",
    name: "ADX (Average Directional Index)",
    category: "Trend",
    formula: "ADX = EMA of DX",
    description: "ดัชนีวัดความแข็งแกร่งของแนวโน้ม ไม่ได้บอกทิศทาง แต่บอกว่าเทรนด์นั้นแรงแค่ไหน",
    recommended_value: "ค่าที่สูงกว่า 25 ถือว่ามีแนวโน้มชัดเจน",
    signal_meaning: {
      bullish: "ADX > 25 และ +DI อยู่เหนือ -DI (เทรนด์ขาขึ้นแข็งแกร่ง)",
      bearish: "ADX > 25 และ -DI อยู่เหนือ +DI (เทรนด์ขาลงแข็งแกร่ง)"
    }
  },
  {
    id: "vol",
    name: "Volume Average",
    category: "Volume",
    formula: "Volume Avg = SMA(Volume, 20)",
    description: "ค่าเฉลี่ยปริมาณการซื้อขาย ใช้ตรวจสอบว่าการเคลื่อนที่ของราคามีแรงสนับสนุนจริงหรือไม่",
    recommended_value: "20 วัน (เปรียบเทียบกับ Volume ปัจจุบัน)",
    signal_meaning: {
      bullish: "ราคาขึ้นพร้อม Volume มากกว่าค่าเฉลี่ย (ยืนยันการขึ้น)",
      bearish: "ราคาลงพร้อม Volume มากกว่าค่าเฉลี่ย (ยืนยันการลง)"
    }
  },
  {
    id: "hh_ll",
    name: "Highest High / Lowest Low",
    category: "Support/Resistance",
    formula: "HH = max(High, 20), LL = min(Low, 20)",
    description: "ราคาสูงสุดและต่ำสุดในช่วงเวลาที่กำหนด ใช้ระบุแนวรับแนวต้านสำคัญ",
    recommended_value: "20 วัน (1 เดือนของการเทรด)",
    signal_meaning: {
      bullish: "ราคาทำ New High เหนือ HH20 (Breakout)",
      bearish: "ราคาทำ New Low ต่ำกว่า LL20 (Breakdown)"
    }
  }
];
