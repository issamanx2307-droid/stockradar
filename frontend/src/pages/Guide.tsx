import { useState } from "react"
import { GUIDE_DATA, GuideItem } from "../data/guideData"

// ── Tab button style ──────────────────────────────────────────────────────────
function tabStyle(active: boolean) {
  return {
    padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer",
    border: `1.5px solid ${active ? "var(--accent)" : "var(--border)"}`,
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--accent)" : "var(--text-muted)",
    transition: "all 0.15s",
  } as React.CSSProperties
}

// ── Guide Tab ─────────────────────────────────────────────────────────────────
function GuideTab() {
  const [selected, setSelected] = useState<GuideItem>(GUIDE_DATA[0])

  return (
    <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16, alignItems: "start" }}>
      {/* Sidebar list */}
      <div className="card" style={{ padding: "12px 8px" }}>
        <div className="card-title" style={{ paddingLeft: 8 }}>รายชื่อเครื่องมือ</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {GUIDE_DATA.map(item => (
            <button key={item.id}
              className={`nav-btn ${selected.id === item.id ? "active" : ""}`}
              onClick={() => setSelected(item)}
              style={{ textAlign: "left" }}>
              <span style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontWeight: 700 }}>{item.id.toUpperCase()}</span>
                <small style={{ fontSize: 10, opacity: 0.6 }}>{item.category}</small>
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div className="card" style={{ padding: "24px 28px" }}>
        <div style={{ marginBottom: 20 }}>
          <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
            background: "var(--accent-dim)", color: "var(--accent)", marginBottom: 8, display: "inline-block" }}>
            {selected.category}
          </span>
          <div style={{ fontSize: 22, fontWeight: 800, color: "var(--accent)", marginTop: 4 }}>{selected.name}</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase",
              letterSpacing: "0.08em", marginBottom: 8 }}>คำอธิบาย</div>
            <p style={{ fontSize: 15, lineHeight: 1.7, color: "var(--text-primary)", margin: 0 }}>
              {selected.description}
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ padding: "14px 16px", background: "var(--bg-elevated)",
              borderRadius: 8, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>สูตรการคำนวณ</div>
              <code style={{ color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
                {selected.formula}
              </code>
            </div>
            <div style={{ padding: "14px 16px", background: "var(--bg-elevated)",
              borderRadius: 8, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>ค่าที่แนะนำ</div>
              <span style={{ color: "#ffd740", fontWeight: 700, fontSize: 14 }}>{selected.recommended_value}</span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
              textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>ความหมายของสัญญาณ</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ padding: "14px 16px", borderLeft: "4px solid var(--green)",
                background: "rgba(0,230,118,0.06)", borderRadius: "0 8px 8px 0" }}>
                <div style={{ color: "var(--green)", fontWeight: 700, marginBottom: 6 }}>🟢 Bullish (ขาขึ้น)</div>
                <p style={{ fontSize: 13, margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                  {selected.signal_meaning.bullish}
                </p>
              </div>
              <div style={{ padding: "14px 16px", borderLeft: "4px solid var(--red)",
                background: "rgba(255,82,82,0.06)", borderRadius: "0 8px 8px 0" }}>
                <div style={{ color: "var(--red)", fontWeight: 700, marginBottom: 6 }}>🔴 Bearish (ขาลง)</div>
                <p style={{ fontSize: 13, margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                  {selected.signal_meaning.bearish}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Menu Guide Data ───────────────────────────────────────────────────────────
interface MenuSection { title: string; items: string[] }
interface MenuItem {
  id: string; icon: string; label: string; color: string
  purpose: string
  howBuilt: string[]
  sections: MenuSection[]
}

const MENU_GUIDE: MenuItem[] = [
  {
    id: "dashboard", icon: "📡", label: "ราดาร์", color: "var(--accent)",
    purpose: "หน้าหลักของแอป — แสดงภาพรวมตลาดแบบ real-time ว่าวันนี้มีหุ้นส่งสัญญาณอะไรบ้าง ใช้เป็นจุดเริ่มต้นทุกวันก่อนเปิดตลาด",
    howBuilt: [
      "Backend รัน Scanner Engine ทุกคืน (จ–ศ) ประมวลผลหุ้นทุกตัวใน SET/NASDAQ/NYSE แล้วบันทึก Signal ลง Database",
      "Frontend ดึงข้อมูล Signal จาก /api/signals/ + Stats จาก /api/dashboard/ มาแสดงผลแบบ real-time",
      "ระบบกรองได้ทันทีโดยไม่ต้องโหลดหน้าใหม่",
    ],
    sections: [
      { title: "📊 Stats Bar (แถบบนสุด)", items: [
        "หุ้นทั้งหมด — จำนวนหุ้นที่ระบบติดตาม",
        "Bullish / Bearish — นับสัญญาณซื้อ vs ขายขณะนั้น",
        "สัญญาณรวม — หุ้นที่ผ่านเงื่อนไขทั้งหมด",
        "Score เฉลี่ย — คะแนนเฉลี่ยของสัญญาณในมุมมองที่กรอง",
      ]},
      { title: "🎯 เกณฑ์ Score ที่ดี (0–100)", items: [
        "⭐ ≥80 — ดีมาก → โมเมนตัมบวกแรง (แนวโน้มแข็งแกร่งทุกด้าน)",
        "✅ 60–79 — ดี → โมเมนตัมบวก (สัญญาณส่วนใหญ่เป็นบวก)",
        "⚠️ 40–59 — พอใช้ → รอสัญญาณชัด (สัญญาณปะปน รอดูเพิ่ม)",
        "❌ <40 — อ่อน → หลีกเลี่ยง (สัญญาณไม่สนับสนุน)",
        "Hover บน Score bar เพื่อดูคำอธิบาย",
      ]},
      { title: "🗂️ Tab สัญญาณ", items: [
        "ทั้งหมด — ทุกสัญญาณ (ทั้ง LONG และ SHORT)",
        "สัญญาณขาขึ้น 🟢 — LONG เท่านั้น: Golden Cross, Oversold, Breakout, โมเมนตัมบวก",
        "สัญญาณขาลง 🔴 — SHORT เท่านั้น: Death Cross, Overbought, โมเมนตัมลบ",
        "Breakout 🚀 — เฉพาะ Volume พุ่ง > 2x ค่าเฉลี่ย 30 วัน",
        "เฝ้าดู 👁️ — สัญญาณประเภท WATCH / ALERT",
      ]},
      { title: "🎛️ Filter Bar", items: [
        "กรองตาม: ประเภทสัญญาณ / ตลาด (SET, NASDAQ, NYSE) / ช่วงเวลา / Score ขั้นต่ำ",
        "คลิกแถวหุ้นในตาราง → เปิดหน้ากราฟทันที",
        "ตาราง Signal แสดง: รหัสหุ้น, สัญญาณ, ราคา, Stop Loss, Risk %, Score Bar, เวลา",
      ]},
      { title: "📐 Score ของแต่ละประเภทสัญญาณ", items: [
        "⭐ Golden Cross (EMA20>EMA50>EMA200) — score คงที่ 80 เสมอ",
        "💀 Death Cross (EMA20<EMA50<EMA200) — score คงที่ 78 เสมอ",
        "🔵 Oversold (RSI < 30) — score 60–95 ยิ่ง RSI ต่ำ score ยิ่งสูง",
        "🟡 Overbought (RSI > 70) — score 60–95 ยิ่ง RSI สูง score ยิ่งสูง",
        "🚀 Breakout (Volume > 2x avg) — score 65–90 ยิ่ง Volume มาก score ยิ่งสูง",
        "🟢 โมเมนตัมบวก (ราคา > EMA200, RSI > 50) — score 60–86 ขึ้นกับระยะห่างจาก EMA200",
        "🔴 โมเมนตัมลบ (ราคา < EMA200, RSI < 50) — score 60–86 ขึ้นกับระยะห่างจาก EMA200",
      ]},
      { title: "🎯 แนะนำการตั้ง Filter แต่ละกรณี", items: [
        "หา Golden Cross คุณภาพ → Tab: ขาขึ้น | Signal: Golden Cross | Score: 60+ | Days: 30 วัน",
        "หา Oversold เด้งแรง → Tab: ขาขึ้น | Signal: Oversold | Score: 75+ | Days: 7 วัน",
        "หา Breakout จริง → Tab: Breakout | Score: 70+ | Days: 7 วัน (สัญญาณสด)",
        "ดูภาพรวมตลาด → Tab: ทั้งหมด | Signal: (ทุกสัญญาณ) | Score: 60+ | Days: 7 วัน",
        "หลีกเลี่ยง: Score ≥80 + ทุกสัญญาณ + 90 วัน → ผลน้อยเกินไป หรือข้อมูลเก่า",
      ]},
      { title: "⚠️ สิ่งที่ควรรู้", items: [
        "Golden Cross มี score = 80 เสมอ → ตั้ง Score ≥50 หรือ ≥80 ได้ผลเหมือนกัน",
        "Signal ถูกสร้างครั้งเดียวต่อวัน (Celery รัน จ–ศ หลังตลาดปิด)",
        "Days filter กรองวันที่สร้าง Signal ไม่ใช่วันที่ราคาเกิด",
        "แต่ละ symbol แสดงผลเพียง 1 signal ที่ดีที่สุด (ไม่ซ้ำหุ้น)",
        "Stop Loss / Risk % ว่าง (-) หมายถึงยังไม่ได้คำนวณ → ใช้หน้า วิเคราะห์หุ้น แทน",
      ]},
      { title: "🌏 Sidebar: สัญญาณตามตลาด", items: [
        "Progress bar แสดงสัดส่วนสัญญาณในแต่ละตลาด (SET / NASDAQ / NYSE)",
      ]},
    ],
  },
  {
    id: "engine_scan", icon: "🔥", label: "ตัวอย่างผลสแกนที่เข้าเกณฑ์", color: "#ff6d00",
    purpose: "ค้นหาหุ้นที่ดีที่สุดในขณะนี้โดยใช้ระบบคะแนน 5 ปัจจัย (5-Factor Scoring Engine) — ไม่ใช่แค่สัญญาณ แต่จัดอันดับว่าหุ้นไหนผ่านมากที่สุดในด้าน Trend, Momentum, Volume, Volatility และ Risk",
    howBuilt: [
      "Engine ที่ /engine/scan/ ดึง candidate symbols จาก Signal table ในช่วงเวลาที่เลือก แล้วคำนวณ Score 0–100 สดด้วย analyze() pipeline เดียวกับหน้าวิเคราะห์หุ้น (Redis cache 60 วิ)",
      "Score Breakdown: Trend (max 40) + Momentum (max 25) + Volume (max 15) + Volatility (max 10) + Risk Penalty",
      "ผลแสดงเป็น Card Grid เรียงตาม Score สูงสุด พร้อม Autocomplete ค้นหารหัสหุ้น",
    ],
    sections: [
      { title: "🎛️ Filter Controls", items: [
        "ตลาด: ทุกตลาด / SET 🇹🇭 / NYSE / NASDAQ 🇺🇸",
        "Score ขั้นต่ำ: All / ≥40 พอใช้ / ≥60 ดี / ≥80 ดีมาก",
        "Top N: 10 / 20 / 50 / 100 หุ้น",
        "ช่วงเวลา: 7 / 14 / 30 / 60 / 90 วัน",
        "ค้นหา: พิมพ์รหัสหุ้น (มี Autocomplete)",
      ]},
      { title: "🎯 เกณฑ์ Score 5-Factor (0–100)", items: [
        "⭐ ≥80 ดีมาก — Trend แข็ง, Momentum บวก, Volume สูง",
        "✅ 60–79 ดี — สัญญาณส่วนใหญ่เป็นบวก น่าพิจารณา",
        "⚠️ 40–59 พอใช้ — มีสัญญาณปะปน รอยืนยันเพิ่ม",
        "❌ <40 อ่อน — สัญญาณไม่เพียงพอ ควรหลีกเลี่ยง",
      ]},
      { title: "📉 Score Breakdown (4 ด้าน)", items: [
        "📈 Trend (max 40): ≥30 ดีมาก · ≥20 ดี · <15 อ่อน",
        "🚀 Momentum (max 25): ≥18 ดีมาก · ≥12 ดี · <8 อ่อน",
        "📢 Volume (max 15): ≥10 ดีมาก · ≥7 ดี · <5 อ่อน",
        "⚡ Volatility (max 10): ≥7 ดีมาก · ≥5 ดี · <3 อ่อน",
      ]},
      { title: "🃏 ScoreCard + Analyze Panel", items: [
        "คลิก Card → เปิด Analyze Panel แบบ popup",
        "แสดง: Score Ring + grade label (ดีมาก/ดี/พอใช้/อ่อน)",
        "Entry / Stop Loss / Risk % / RSI / ADX",
        "เหตุผลที่ Engine เลือกหุ้นนี้ (ภาษาไทย)",
        "ปุ่ม 📈 กราฟ เปิดหน้ากราฟต่อได้ทันที",
      ]},
      { title: "📊 Summary Badges", items: [
        "ด้านบน Grid นับจำนวนหุ้นตามประเภทสัญญาณ: โมเมนตัมบวกแรง / โมเมนตัมบวก / รอสัญญาณชัด / เฝ้าดู / โมเมนตัมลบ",
      ]},
    ],
  },
  {
    id: "watchlist", icon: "⭐", label: "Watchlist", color: "#ffd600",
    purpose: "สมุดบันทึกการซื้อขายส่วนตัว — ใส่หุ้นที่ซื้อจริง บันทึกราคา+จำนวน แล้วให้ระบบติดตาม P/L และแนะนำว่าควร ถือ / ซื้อเพิ่ม / ขายทำกำไร / ตัดขาดทุน",
    howBuilt: [
      "Backend /api/watchlist/ เก็บ Trade History ของแต่ละ user",
      "คำนวณ: ต้นทุนเฉลี่ย (avg_cost), กำไร/ขาดทุน unrealized, market value, Stop Loss อิงจาก ATR",
      "Engine วิเคราะห์แต่ละหุ้นใน Watchlist เพื่อแนะนำ action",
      "/api/watchlist/history/ ดึง P/L ย้อนหลังวาดกราฟ SVG",
    ],
    sections: [
      { title: "➕ เพิ่มหุ้น (สูงสุด 10 ตัว)", items: [
        "พิมพ์รหัสหุ้น → เลือกจาก Autocomplete",
        "กรอก: ราคาซื้อ, จำนวนหุ้น, วันที่, หมายเหตุ",
        "บันทึก Trade ซ้ำหลายครั้งได้ → ระบบคำนวณต้นทุนเฉลี่ยอัตโนมัติ",
      ]},
      { title: "📋 ข้อมูลแต่ละหุ้น", items: [
        "ต้นทุนเฉลี่ย — คำนวณจากทุก Trade ที่บันทึก",
        "ราคาปัจจุบัน — ดึงจาก DB (อัปเดตรายวัน)",
        "Unrealized P/L — กำไร/ขาดทุนที่ยังไม่ realise เป็น ฿ และ %",
        "Stop Loss — คำนวณจาก ATR อัตโนมัติ",
        "คำแนะนำ: BUY_MORE 🟢 / HOLD 🟡 / TAKE_PROFIT 🔵 / SELL 🔴",
        "เหตุผลอธิบายว่าทำไมถึงแนะนำอย่างนั้น",
        "ค่า RSI / ADX / EMA20 / EMA50 / EMA200 ปัจจุบัน",
      ]},
      { title: "📈 P/L History Chart", items: [
        "กราฟ SVG แสดงมูลค่าพอร์ตย้อนหลัง",
        "Hover บนกราฟ → tooltip แสดงวันที่ + มูลค่า + % กำไร/ขาดทุน",
        "เลือกช่วงเวลา: 7 / 30 / 90 วัน",
      ]},
      { title: "📊 Portfolio Summary", items: [
        "รวม: ต้นทุนทั้งหมด, มูลค่าตลาดรวม, กำไร/ขาดทุนรวม (% รวม)",
      ]},
    ],
  },
  {
    id: "analyze", icon: "🔬", label: "วิเคราะห์หุ้น", color: "#00d4ff",
    purpose: "วิเคราะห์หุ้นตัวเดียวแบบเจาะลึก — ป้อนรหัสหุ้นแล้วรับผลวิเคราะห์เต็มรูปแบบจาก 5-Factor Engine พร้อม Entry Point, Stop Loss, Position Size และเหตุผลเป็นภาษาไทย",
    howBuilt: [
      "เรียก /engine/analyze/{symbol}/ ซึ่งเป็น Real-time calculation (ไม่ใช่แค่ดึง cache)",
      "ส่ง capital ที่ผู้ใช้กรอกเพื่อคำนวณ Position Size ที่เหมาะสม",
      "รองรับทั้งหุ้น SET และ US (NASDAQ/NYSE) ผ่าน Autocomplete",
    ],
    sections: [
      { title: "🔍 ค้นหาหุ้น", items: [
        "พิมพ์รหัสหุ้น (มี Autocomplete ทั้ง SET และ US)",
        "กรอกเงินทุน (฿) ที่ต้องการใช้ → ระบบคำนวณจำนวนหุ้นที่ควรซื้อ",
      ]},
      { title: "📊 ผลวิเคราะห์", items: [
        "ป้ายสัญญาณ: โมเมนตัมบวกแรง / โมเมนตัมบวก / รอสัญญาณชัด / เฝ้าดู / โมเมนตัมลบ",
        "Score 0–100 + Grade label (⭐ดีมาก / ✅ดี / ⚠️พอใช้ / ❌อ่อน)",
        "Entry Price — ราคาที่เหมาะสมในการเข้าซื้อ",
        "Stop Loss — ราคาตัดขาดทุน (อิง ATR) ออกทันทีเมื่อหลุดระดับนี้",
        "Risk % — ≤2% ดี · ≤5% พอใช้ · >5% สูงเกิน",
        "RSI: >70 Overbought · 50–70 Bullish · 30–50 Neutral · <30 Oversold",
        "ADX: >25 มีแนวโน้มแข็งแกร่ง · 20–25 เริ่มมีแนวโน้ม · <20 Sideways",
      ]},
      { title: "📉 Score Breakdown (4 แท่ง)", items: [
        "📈 Trend (max 40): ≥30 ดีมาก · ≥20 ดี · <15 อ่อน",
        "🚀 Momentum (max 25): ≥18 ดีมาก · ≥12 ดี · <8 อ่อน",
        "📢 Volume (max 15): ≥10 ดีมาก · ≥7 ดี · <5 อ่อน",
        "⚡ Volatility (max 10): ≥7 ดีมาก · ≥5 ดี · <3 อ่อน",
        "⚠️ Risk Penalty — หักคะแนนเมื่อ Risk % สูงเกิน",
      ]},
      { title: "✅ เหตุผลสนับสนุน", items: [
        "รายการ bullet point อธิบายว่าหุ้นผ่านเงื่อนไขอะไรบ้าง",
        "เช่น: ราคาเหนือ EMA200, RSI ยังไม่ Overbought, Volume สูงกว่าค่าเฉลี่ย 1.8x",
      ]},
    ],
  },
  {
    id: "fundamental", icon: "📊", label: "Fundamental", color: "#ce93d8",
    purpose: "ดูข้อมูลพื้นฐานบริษัท — งบการเงิน, อัตราส่วนการลงทุน, ความเห็นนักวิเคราะห์ สำหรับนักลงทุนที่ไม่ได้เล่นเทคนิคอย่างเดียว",
    howBuilt: [
      "Backend ดึงข้อมูลจาก Yahoo Finance API สำหรับข้อมูลพื้นฐาน",
      "Cache ผลลัพธ์ไว้ใน Redis เพื่อไม่ให้ดึงซ้ำทุกครั้ง",
      "รองรับเฉพาะหุ้น US (NYSE/NASDAQ) ในระยะแรก",
    ],
    sections: [
      { title: "📌 ข้อมูลบริษัท", items: [
        "ชื่อ, Sector, Industry, ประเทศ, จำนวนพนักงาน",
        "คำอธิบายธุรกิจ",
      ]},
      { title: "💰 อัตราส่วนมูลค่า (Valuation)", items: [
        "P/E Trailing / Forward — ราคาเทียบกำไรปัจจุบัน/คาดการณ์",
        "P/B Ratio — ราคาเทียบมูลค่าตามบัญชี",
        "EV/EBITDA — มูลค่ากิจการเทียบกำไรก่อนดอกเบี้ย",
        "Market Cap — มูลค่าตลาดรวม",
        "PEG Ratio — P/E เทียบอัตราเติบโต",
      ]},
      { title: "📈 งบกำไรขาดทุน + ความแข็งแกร่ง", items: [
        "Revenue, Gross Profit, Net Income",
        "Profit Margin, Gross Margin, Operating Margin",
        "ROE, ROA, Debt/Equity, Current Ratio, Quick Ratio",
        "Operating Cash Flow, Free Cash Flow",
      ]},
      { title: "🎯 ความเห็นนักวิเคราะห์", items: [
        "จำนวนนักวิเคราะห์, ราคาเป้าหมาย (mean/high/low)",
        "Consensus: Strong Buy / Buy / Hold / Sell",
        "Bar chart แสดงสัดส่วนความเห็นแต่ละประเภท",
      ]},
      { title: "📅 งบรายไตรมาส", items: [
        "ตาราง 4–8 ไตรมาสล่าสุด: Revenue, Gross Profit, Net Income",
      ]},
      { title: "🎯 เกณฑ์อัตราส่วนที่ดี", items: [
        "P/E: <15 ถูก · 15–25 สมเหตุ · >25 แพง (ขึ้นกับ sector)",
        "ROE: >15% ดีมาก · >10% ดี · <5% ต่ำ",
        "Profit Margin: >20% ดีมาก · >10% ดี · <5% ต่ำ",
        "Debt/Equity: <0.5 ดี · 0.5–1.5 พอใช้ · >2 เสี่ยง",
        "Revenue Growth: >20% ดีมาก · >10% ดี · ติดลบ = ต้องระวัง",
      ]},
    ],
  },
  {
    id: "portfolio", icon: "💼", label: "Portfolio", color: "#69f0ae",
    purpose: "สร้างพอร์ตอัตโนมัติ — กรอกเงินทุนที่มี ระบบจะสแกนหุ้นที่ผ่าน Score สูงสุด แล้วจัดสรรว่าควรซื้อหุ้นไหน เท่าไหร่ ด้วยเงินเท่าไหร่",
    howBuilt: [
      "เรียก /engine/portfolio/run/ ส่ง: capital, exchange, min_score",
      "Engine สแกนหุ้น → เรียงตาม Score → จัดสรรเงินตามสัดส่วน Score",
      "คำนวณ Position Size แต่ละตัว พร้อม Entry / Stop Loss",
    ],
    sections: [
      { title: "⚙️ ตั้งค่าก่อน Run", items: [
        "เงินทุน (฿) — ใส่ทุนทั้งหมดที่มี เช่น 1,000,000",
        "ตลาด — SET / NYSE / NASDAQ หรือทุกตลาด",
        "Score ขั้นต่ำ — เช่น ≥60 = เลือกเฉพาะหุ้นคุณภาพสูง",
      ]},
      { title: "📊 Portfolio Summary", items: [
        "เงินสด (Cash) — ที่เหลือหลังจัดสรร",
        "เงินลงทุน — ที่ใส่ไปในหุ้น",
        "Market Value — มูลค่าตลาดทันที",
        "Unrealized P/L — กำไร/ขาดทุนทันที",
        "จำนวน Position — หุ้นกี่ตัวในพอร์ต",
      ]},
      { title: "📋 ตาราง Position แต่ละตัว", items: [
        "รหัสหุ้น, Decision Badge, ราคาซื้อ, จำนวนหุ้น, Stop Loss, ต้นทุนรวม",
        "คลิก 📈 เปิดกราฟได้ทันที",
      ]},
      { title: "🎯 ตั้ง Score ขั้นต่ำอย่างไร", items: [
        "≥60 — แนะนำสำหรับพอร์ตที่ต้องการคุณภาพ",
        "≥70 — สำหรับนักลงทุนที่ conservative",
        "≥80 — เลือกเฉพาะหุ้น top tier (จำนวนน้อยลงแต่คุณภาพสูง)",
      ]},
    ],
  },
  {
    id: "multi_layer", icon: "🎯", label: "Multi-Layer Scanner", color: "#7c4dff",
    purpose: "สแกนหุ้นผ่าน 4 ด่านพร้อมกัน — ไม่ใช่แค่ตัวเลข Score แต่บอกได้ว่าหุ้นผ่านหรือไม่ผ่านด่านไหน และทำไม เหมาะสำหรับหาจุดเข้าที่มีเหตุผลรองรับหลายด้านพร้อมกัน",
    howBuilt: [
      "Layer 1 (Trend): ตรวจ EMA20/50/200 alignment — ถ้า EMA20>EMA50>EMA200 = Strong Uptrend",
      "Layer 2 (Structure): คำนวณ Pivot Points + หา Dynamic S/R จาก Local High/Low ที่ราคาแตะ ≥ 2 ครั้งใน 60 วัน",
      "Layer 3 (Pattern): ตรวจ Candlestick 6 แบบ จาก OHLC ล้วนๆ ได้แก่ Hammer, Shooting Star, Bullish/Bearish Engulfing, Doji, Pin Bar",
      "Layer 4 (Momentum): RSI zone + MACD Histogram direction — ตรวจว่า momentum สนับสนุน setup ไหม",
      "ผลลัพธ์: layers_passed (0-4), setup (BUY/SELL/WATCH/NEUTRAL), confidence (HIGH/MEDIUM/LOW)",
    ],
    sections: [
      { title: "🔄 ลำดับการกรอง (Filter Chain)", items: [
        "📈 Layer 1 Trend → ตอบว่า 'เทรนด์ไปทางไหน?'",
        "🏗️ Layer 2 Structure → ตอบว่า 'ราคาอยู่จุดไหนของโครงสร้าง?'",
        "🕯️ Layer 3 Pattern → ตอบว่า 'มี Signal เข้าจริงไหม?'",
        "⚡ Layer 4 Momentum → ตอบว่า 'momentum สนับสนุนไหม?'",
        "หุ้นที่ผ่านทั้ง 4 layer = Setup ที่มีเหตุผลรองรับรอบด้าน",
      ]},
      { title: "🟢 Layer 1 — Trend (EMA)", items: [
        "STRONG_UP: EMA20 > EMA50 > EMA200 + ราคาเหนือ EMA50 → ผ่าน ✅",
        "WEAK_UP: EMA20 > EMA50 แต่ยังต่ำกว่า EMA200 → ผ่าน ✅ (เพิ่งฟื้น)",
        "STRONG_DOWN: EMA20 < EMA50 < EMA200 → ผ่าน ✅ สำหรับ SELL setup",
        "SIDEWAYS: EMA20 ≈ EMA50 (ห่าง < 1%) → ไม่ผ่าน ❌",
      ]},
      { title: "🏗️ Layer 2 — Structure (S/R)", items: [
        "Pivot Points: PP, R1, R2, S1, S2 คำนวณจาก High/Low/Close วันก่อน",
        "Dynamic S/R: หา Local High/Low ใน 60 วันที่ราคาแตะซ้ำ ≥ 2 ครั้ง",
        "BUY pass: ราคาใกล้แนวรับ ≤ 3% และไม่ชนแนวต้าน",
        "SELL pass: ราคาใกล้แนวต้าน ≤ 3% และไม่อยู่เหนือแนวรับ",
        "Popup รายละเอียดจะแสดง Level ทุกเส้นพร้อมสี S=เขียว R=แดง",
      ]},
      { title: "🕯️ Layer 3 — Pattern (Candlestick)", items: [
        "Hammer 🔨: ไส้ล่าง > 2× body, ไส้บน < 30% body → กลับตัวขาขึ้น",
        "Shooting Star ⭐: ไส้บน > 2× body, ไส้ล่าง < 30% body → กลับตัวขาลง",
        "Bullish Engulfing 🟢: แท่งบวกกลืนแท่งลบวันก่อน (body ≥ 110%)",
        "Bearish Engulfing 🔴: แท่งลบกลืนแท่งบวกวันก่อน (body ≥ 110%)",
        "Doji ➕: body < 10% ของ range — ลังเล จุดพลิก (ไม่นับว่าผ่าน รอ confirm)",
        "Pin Bar 📌: ไส้ยาว > 60% ของ range ทั้งแท่ง",
      ]},
      { title: "⚡ Layer 4 — Momentum (RSI + MACD)", items: [
        "BUY pass: RSI 40-65 (ยังมีที่ไป) + MACD Hist > 0 หรือกำลังขึ้น",
        "Oversold Recovery: RSI < 35 + MACD กำลังเด้ง → pass (โอกาส bounce)",
        "SELL pass: RSI 35-60 + MACD Hist < 0 หรือกำลังลง",
        "RSI > 70 = Overbought → ไม่ผ่านสำหรับ BUY setup",
        "RSI < 35 = Oversold → ไม่ผ่านสำหรับ SELL setup (เสี่ยงเด้ง)",
      ]},
      { title: "📊 Setup & Confidence", items: [
        "BUY: Trend=UP + ผ่าน ≥ 3 layers → setup = BUY",
        "SELL: Trend=DOWN + ผ่าน ≥ 3 layers → setup = SELL",
        "WATCH_BUY / WATCH_SELL: ผ่านแค่ 2 layers → รอสัญญาณเพิ่ม",
        "HIGH confidence: ผ่านครบ 4/4 layers",
        "MEDIUM: 3/4 | LOW: 2/4 | NONE: 0-1/4",
      ]},
      { title: "💡 วิธีใช้งานแนะนำ", items: [
        "กรอง: SET + min 3 Layer + Setup = BUY → หาหุ้นที่สมบูรณ์",
        "กดที่แถวหุ้นเพื่อดู popup รายละเอียดทุก Layer",
        "ใช้ร่วมกับ Analyze เพื่อดู Score, Entry, Stop Loss ก่อนตัดสินใจ",
        "ข้อมูลอิง OHLCV + Indicator ปัจจุบัน (ไม่ใช่ Signal Database)",
        "Cache 5 นาที — กดสแกนใหม่เพื่อรีเฟรชข้อมูล",
      ]},
    ],
  },
  {
    id: "scanner", icon: "🔍", label: "สแกนหุ้น", color: "var(--green)",
    purpose: "ค้นหาหุ้นตามเงื่อนไขทางเทคนิคที่กำหนดเอง — ยืดหยุ่นกว่า Radar ตรงที่ผู้ใช้กำหนด filter ได้เอง ทั้งแบบ preset formula และแบบเขียนเองได้",
    howBuilt: [
      "Backend /api/scanner/ รับ params แล้วสแกนจาก Indicator table + PriceDaily โดยตรง (ไม่ใช่ Signal Database)",
      "รองรับ Formula Parser: rsi(14) < 30, close > ema(200), macd_hist > 0 ฯลฯ",
      "Filter เสริม: ADX, Volume, ATR (เปิด/ปิดได้)",
    ],
    sections: [
      { title: "🎛️ Filter หลัก", items: [
        "ตลาด: SET / NASDAQ / NYSE",
        "ประเภทสัญญาณ: Golden Cross, Breakout, Oversold ฯลฯ",
        "ทิศทาง: LONG / SHORT",
        "Score ขั้นต่ำ, ADX ขั้นต่ำ, RSI min/max",
      ]},
      { title: "📐 Formula Presets", items: [
        "📈 ราคาเหนือ EMA 200 (ขาขึ้น)",
        "🔵 RSI Oversold (< 30)",
        "🟡 RSI Overbought (> 70)",
        "💥 Volume สูง (2x Avg)",
        "🚀 ราคาเบรค New High 20 วัน",
        "📶 MACD ตัดขึ้น (Bullish)",
        "🛡️ ADX แข็งแกร่ง (> 25)",
      ]},
      { title: "📊 ตารางผลลัพธ์", items: [
        "รหัสหุ้น + ชื่อ, Signal Badge, ทิศทาง (LONG/SHORT)",
        "ราคา, Stop Loss + Risk %, RSI, ADX",
        "Filter Badges: ✓ Volume / ✓ ATR / ✓ ADX",
        "คลิก 📈 เปิดกราฟ | คลิก 🔬 เปิดวิเคราะห์",
      ]},
      { title: "🎯 เกณฑ์ค่าที่ดีสำหรับ Filter", items: [
        "Score ≥60 — จุดเริ่มต้นที่แนะนำสำหรับผู้เริ่มต้น",
        "ADX ≥25 — หมายถึงมีแนวโน้มชัดเจน (ดีกว่า Sideways)",
        "RSI 40–60 — zone กลาง ยังไม่ Overbought/Oversold",
        "RSI <30 — Oversold อาจ bounce กลับ (สัญญาณซื้อ)",
        "RSI >70 — Overbought ระวังแนวต้าน (ไม่แนะนำเข้าใหม่)",
      ]},
    ],
  },
  {
    id: "strategy", icon: "🎯", label: "กลยุทธ์", color: "#ff9100",
    purpose: "สร้างกลยุทธ์การลงทุนเอง — กำหนดเงื่อนไข Indicator หลายข้อ แล้วสั่งให้ระบบสแกนว่าหุ้นไหนตรงตามกลยุทธ์นั้น รองรับทั้งหุ้นไทย (SET) และหุ้น US (NASDAQ/NYSE)",
    howBuilt: [
      "กลยุทธ์ถูกแปลงเป็น Condition Set ส่งไปที่ Backend",
      "Backend ประเมินทุกหุ้นว่าผ่านเงื่อนไข AND/OR ครบไหม",
      "มี Preset Strategy สำเร็จรูป 8 แบบให้เลือกได้ทันที",
      "ข้อมูลหุ้น US ดึงจาก Alpaca Market Data API โดยตรง",
    ],
    sections: [
      { title: "📚 Preset Strategies (8 แบบ)", items: [
        "⭐ MA Cross — Bullish: EMA20 > EMA50 > EMA200 + RSI > 45",
        "🔵 RSI Oversold Bounce: RSI < 30 + ราคาเหนือ EMA200",
        "📶 MACD Bullish Cross: MACD Line > Signal + MACD Hist > 0",
        "🚀 Bollinger Breakout: ราคาทะลุ BB Upper + Volume > avg",
        "💀 Death Cross — Bearish: EMA20 < EMA50 < EMA200 + RSI < 50",
        "💥 Volume Spike: Volume > 2x ค่าเฉลี่ย + RSI > 50",
        "📈 ADX Strong Trend: ADX > 25 + DI+ > DI− + RSI > 50 (เทรนด์ขาขึ้นแข็งแกร่ง)",
        "📉 ADX Trend Reversal: ADX > 25 + DI− > DI+ + RSI < 45 (เทรนด์ขาลง)",
      ]},
      { title: "🛠️ สร้างกลยุทธ์เอง", items: [
        "Indicator (15 ตัว): EMA20/50/200, RSI, MACD Line/Signal/Hist, BB Upper/Lower, ATR(14), ADX(14), DI+, DI−, Volume, Volume Ratio",
        "Operator (7 แบบ): > มากกว่า, ≥ มากกว่าเท่ากับ, < น้อยกว่า, ≤ น้อยกว่าเท่ากับ, = เท่ากับ, ข้ามขึ้น ↑, ข้ามลง ↓",
        "Target: Indicator อีกตัว (เช่น DI+ > DI−) หรือค่าตัวเลข (เช่น RSI > 50)",
        "Logic: AND (ต้องครบทุกข้อ)",
        "เพิ่มเงื่อนไขได้ไม่จำกัด",
      ]},
      { title: "📊 Indicator ใหม่: ATR / ADX / DI", items: [
        "ATR (14) — วัดความผันผวนเฉลี่ย 14 วัน ใช้กำหนด Stop Loss",
        "ADX (14) — วัดความแข็งแกร่งของเทรนด์ (>25 = เทรนด์ชัด, <20 = Sideways)",
        "DI+ — แรงซื้อ (Positive Directional Indicator)",
        "DI− — แรงขาย (Negative Directional Indicator)",
        "DI+ > DI− = ขาขึ้น | DI− > DI+ = ขาลง",
        "ใช้ ADX + DI ร่วมกันเพื่อยืนยันทิศทางและความแรงของเทรนด์",
      ]},
      { title: "▶️ Run Strategy", items: [
        "กด Run → ระบบสแกนหุ้นทุกตัวใน Database",
        "ผล: รายชื่อหุ้นที่ผ่านเงื่อนไขทั้งหมด พร้อมรายละเอียด (สูงสุด 20 ตัว)",
        "สัญญาณ 8 แบบ: โมเมนตัมบวกแรง 💚, โมเมนตัมบวก 🟢, โมเมนตัมลบ 🔴, โมเมนตัมลบแรง ❤️, Breakout 🚀, Oversold 🔵, Overbought 🟡, เฝ้าดู 👁️",
      ]},
    ],
  },
  {
    id: "backtest", icon: "⏪", label: "Backtest", color: "#29b6f6",
    purpose: "ทดสอบกลยุทธ์กับข้อมูลย้อนหลัง — ก่อนลงทุนจริง ให้ระบบจำลองว่าถ้าใช้กลยุทธ์นี้ในอดีต จะได้กำไรหรือขาดทุนเท่าไหร่ และมีความเสี่ยงอย่างไร",
    howBuilt: [
      "Backend /api/backtest/ รัน simulation บน Price History ใน Database",
      "รองรับ 2 Mode: Signal Mode (ออกเมื่อเกิด SELL Signal) และ SL/TP Mode (ออกเมื่อถึง Stop Loss หรือ Take Profit)",
      "วาด Equity Curve ด้วย SVG interactive (Hover แสดง tooltip)",
    ],
    sections: [
      { title: "⚙️ ตั้งค่า Backtest", items: [
        "รหัสหุ้น — หุ้นที่จะทดสอบ",
        "เงินทุนเริ่มต้น — เช่น ฿100,000",
        "ช่วงเวลา — วันเริ่มต้น → วันสิ้นสุด",
        "Mode — Signal หรือ SL/TP",
        "Stop Loss % / Take Profit % (ถ้าใช้ SL/TP Mode)",
      ]},
      { title: "📊 แท็บ สถิติ", items: [
        "กำไรรวม (%) — ผลตอบแทนตลอดช่วงเวลา",
        "Win Rate — % trades ที่กำไร",
        "Max Drawdown — ขาดทุนสูงสุดจากจุดสูงสุด",
        "Sharpe Ratio — ผลตอบแทนเทียบความเสี่ยง (≥1 = ดี)",
        "Profit Factor — กำไรรวม ÷ ขาดทุนรวม (≥1.5 = ดี)",
        "เทียบกับ Buy & Hold ถ้าซื้อแล้วถือตลอด",
      ]},
      { title: "📈 แท็บ Equity Curve", items: [
        "กราฟแสดงมูลค่าพอร์ตในแต่ละวัน",
        "Hover → tooltip แสดงวันที่ + มูลค่า + %",
        "เส้นประแสดง initial capital เป็นฐาน",
      ]},
      { title: "📋 แท็บ Trade Log", items: [
        "ตารางทุก Trade: วันเข้า/ออก, ราคา, กำไร/ขาดทุน",
        "เหตุผลออก: Stop Loss / Take Profit / SELL Signal / End",
        "กด ดูทั้งหมด เพื่อแสดงครบทุก trade",
      ]},
      { title: "🎯 เกณฑ์ Backtest ที่ดี", items: [
        "กำไรรวม: ≥20% ดีมาก · ≥10% ดี · ≥0% พอใช้ · ติดลบ = กลยุทธ์ไม่ดี",
        "Win Rate: ≥60% ดีมาก · ≥50% ดี · <40% แย่ (ต่ำกว่า 50% ขาดทุนในระยะยาว)",
        "Max Drawdown: <10% ดีมาก · <20% ดี · >30% อันตราย (ทนไม่ได้ในทางจิตใจ)",
        "Sharpe Ratio: ≥2 ดีมาก · ≥1 ดี · ≥0.5 พอใช้ · <0 แย่กว่าฝากธนาคาร",
        "Profit Factor: ≥2 ดีมาก · ≥1.5 ดี · ≥1 คุ้มทุน · <1 ขาดทุนแน่นอน",
        "กำไรเฉลี่ย/trade ควรมากกว่า ขาดทุนเฉลี่ย/trade เสมอ",
        "เปรียบกับ Buy & Hold — กลยุทธ์ควรชนะ Buy & Hold จึงคุ้มค่า",
      ]},
    ],
  },
  {
    id: "how_to_find", icon: "🔎", label: "หาหุ้นน่าซื้อ + จุดเข้า", color: "#00e676",
    purpose: "คู่มือใช้งานระบบแบบ step-by-step — เริ่มจากหาหุ้นที่ผ่านเกณฑ์หลายด้านพร้อมกัน ไปจนถึงหาจุดเข้าซื้อที่มีเหตุผลรองรับ ก่อนกดซื้อจริง",
    howBuilt: [
      "ขั้นที่ 1 — เปิด Multi-Layer Scanner: เลือกตลาด (SET/NASDAQ/NYSE) + min 3 Layer + Setup = คะแนนดี → กดสแกน",
      "ขั้นที่ 2 — ดูคอลัมน์ Setup: เลือกหุ้นที่เป็น 'คะแนนดีมาก' (4/4) ก่อน รองลงมา 'คะแนนดี' (3/4)",
      "ขั้นที่ 3 — คลิกที่แถวหุ้น → ดู popup ว่าผ่าน/ไม่ผ่าน Layer ไหน และทำไม",
      "ขั้นที่ 4 — เปิดหน้า วิเคราะห์หุ้น 🔬 ใส่รหัสหุ้น + เงินทุน → ดู Entry Price, Stop Loss, Risk %",
      "ขั้นที่ 5 — ดู Chart 📈 ยืนยันด้วยตา ว่าราคาอยู่เหนือ EMA + ไม่ชนแนวต้านใหญ่",
    ],
    sections: [
      { title: "🎯 เกณฑ์คัดหุ้นก่อนเข้าซื้อ", items: [
        "Score ≥ 60 — สัญญาณส่วนใหญ่เป็นบวก (ดูจากหน้า วิเคราะห์หุ้น)",
        "ADX ≥ 25 — มีแนวโน้มชัดเจน ไม่ใช่ Sideways",
        "RSI ไม่เกิน 70 — ยังไม่ Overbought มีที่ไป",
        "Layer 1 Trend ผ่าน — EMA ยืนยันทิศทาง",
        "Layer 2 Structure ผ่าน — ราคาใกล้แนวรับ ไม่ชนแนวต้าน",
        "Risk % ≤ 2% ต่อ Trade — ไม่รับความเสี่ยงเกินที่รับได้",
      ]},
      { title: "📍 วิธีหาจุดเข้าซื้อ", items: [
        "Entry Price จาก วิเคราะห์หุ้น = ราคาปิดล่าสุด (ใช้เป็น reference)",
        "รอ Pullback มาแตะ EMA20 หรือแนวรับใกล้สุด (Layer 2) แล้วเข้า",
        "ถ้า Candlestick Layer 3 = Hammer หรือ Bullish Engulfing → ยิ่งดี เข้าได้เลย",
        "ถ้าราคา Breakout เหนือ Resistance เก่า + Volume สูง → เข้าทันทีที่ close เหนือแนว",
        "หลีกเลี่ยงเข้าตอน RSI > 65 หรือราคาห่าง EMA20 > 5% — overextended",
      ]},
      { title: "🔄 Workflow แนะนำ (ทำทุกวัน)", items: [
        "7:00 เปิด Dashboard ดูภาพรวมตลาด — Bullish vs Bearish สัดส่วน",
        "8:30 เปิด Multi-Layer Scanner SET + 3 Layer → บันทึก watchlist เบื้องต้น",
        "9:00 วิเคราะห์หุ้นแต่ละตัวใน วิเคราะห์หุ้น + เปิด Chart ยืนยัน",
        "9:30 ตลาดเปิด — เฝ้าดูราคาเทียบกับ Entry ที่ได้เตรียมไว้",
        "หลังปิดตลาด — เพิ่มหุ้นที่ซื้อเข้า Watchlist บันทึก Trade",
      ]},
      { title: "⚠️ ข้อควรระวัง", items: [
        "ระบบใช้ข้อมูล End-of-Day — ราคา real-time ต้องดูจากโบรกเกอร์โดยตรง",
        "สัญญาณดี ≠ รับประกันกำไร — ตลาดมีปัจจัยภายนอกที่ระบบไม่รู้",
        "ห้ามซื้อพร้อมกันหลายหุ้นโดยไม่ดู Risk % รวม — ควรไม่เกิน 6% รวมทุก Trade",
        "ถ้าตลาดโดยรวม Bearish (Bearish > Bullish มาก) → ลด position size ลง",
        "ใช้ Backtest ทดสอบ pattern ที่สนใจก่อนใช้เงินจริง",
      ]},
    ],
  },
  {
    id: "stop_loss_guide", icon: "🛡️", label: "Stop Loss ที่เหมาะสม", color: "#ff6d00",
    purpose: "อธิบายวิธีใช้ Stop Loss จากระบบให้ถูกต้อง — ระบบคำนวณ Stop Loss ให้อัตโนมัติทุกหุ้น แต่ผู้ใช้ต้องเข้าใจว่ามันคำนวณมาอย่างไร และตั้งใช้จริงอย่างไร",
    howBuilt: [
      "Stop Loss ในระบบนี้คำนวณจาก ATR14 (Average True Range 14 วัน) × 2.0",
      "ATR วัดความผันผวนเฉลี่ยรายวัน — หุ้นผันผวนมาก Stop Loss จะห่างกว่า",
      "สูตร: Stop Loss = ราคาปัจจุบัน − (ATR14 × 2.0)",
      "แสดงผลใน: วิเคราะห์หุ้น 🔬, Watchlist ⭐, Portfolio 💼, Scanner 🔍",
      "Risk % = (ราคาซื้อ − Stop Loss) / ราคาซื้อ × 100",
    ],
    sections: [
      { title: "📖 Stop Loss คืออะไร ทำไมต้องตั้ง", items: [
        "Stop Loss = ระดับราคาที่ยอมรับว่า 'วิเคราะห์ผิด' และต้องออกทันที",
        "ป้องกันขาดทุนใหญ่จากกรณีที่ตลาดเคลื่อนที่ผิดทิศทาง",
        "ไม่มี Stop Loss = ถือต่อไปเรื่อยๆ จนอาจขาดทุนกลับไปที่ 0",
        "Rule: ออก ณ Stop Loss เสมอ — ห้ามเลื่อน Stop Loss ลงเพื่อรอ",
      ]},
      { title: "📊 วิธีอ่าน Stop Loss จากระบบ", items: [
        "หน้า วิเคราะห์หุ้น → ช่อง Stop Loss แสดงราคาตัดขาดทุน",
        "Risk % แสดงทันทีว่าถ้าโดน Stop ขาดทุนกี่ % จากราคาซื้อ",
        "Risk % ≤ 2% = ดี (ขาดทุนน้อยต่อ Trade)",
        "Risk % 2–5% = พอรับได้ แต่ต้องลด Position Size ลง",
        "Risk % > 5% = หุ้นผันผวนสูง — ควรลด lot หรือข้ามไปหุ้นตัวอื่น",
      ]},
      { title: "💰 คำนวณ Position Size จาก Stop Loss", items: [
        "สูตร: จำนวนหุ้น = (เงินทุน × Risk ต่อ Trade%) ÷ (ราคาซื้อ − Stop Loss)",
        "ตัวอย่าง: ทุน ฿100,000, Risk 1% = ฿1,000 ต่อ Trade",
        "ราคาซื้อ 10 บาท, Stop Loss 9.50 บาท → Risk ต่อหุ้น = 0.50 บาท",
        "จำนวนหุ้น = ฿1,000 ÷ ฿0.50 = 2,000 หุ้น (ลงทุน ฿20,000)",
        "ระบบคำนวณให้อัตโนมัติเมื่อกรอกเงินทุนในหน้า วิเคราะห์หุ้น",
      ]},
      { title: "🎯 การใช้ Stop Loss ในแต่ละหน้า", items: [
        "วิเคราะห์หุ้น 🔬 — Stop Loss + Risk % + Position Size แนะนำ ครบในที่เดียว",
        "Watchlist ⭐ — คำนวณ Stop Loss ใหม่ทุกวัน (ATR เปลี่ยนตามตลาด)",
        "Scanner 🔍 — คอลัมน์ Stop Loss + Risk % ในตาราง กรองได้ตาม Risk",
        "Portfolio 💼 — จัดสรร Position แต่ละตัวโดยคำนึง Stop Loss อัตโนมัติ",
      ]},
      { title: "⚠️ ข้อควรระวังเรื่อง Stop Loss", items: [
        "Stop Loss จาก ATR เป็นแค่จุดอ้างอิง — อาจปรับได้ตาม S/R ที่เห็นในกราฟ",
        "ห้ามเลื่อน Stop Loss ลงเพื่อ 'รอให้หุ้นกลับ' — เป็นนิสัยที่ทำให้ขาดทุนหนัก",
        "ถ้าราคาหลุด Stop แล้วกลับขึ้น — ก็ยังถูก เพราะไม่รู้ก่อนว่าจะกลับ",
        "หุ้นปันผล/หุ้นพัก — ATR อาจต่ำมาก Stop Loss แคบเกิน ควรใช้ S/R แทน",
        "Trailing Stop: เลื่อน Stop ขึ้นตามราคาที่ขึ้น แต่ห้ามเลื่อนลง",
      ]},
    ],
  },
  {
    id: "ai_chat", icon: "🤖", label: "คุยกับเอไอ", color: "#7c4dff",
    purpose: "ถามคำถามเกี่ยวกับหุ้นเป็นภาษาไทยกับ AI — วิเคราะห์หุ้น, แนะนำหุ้นน่าซื้อ, อธิบาย indicator, เสนอ order ซื้อ/ขาย ผ่าน Alpaca Paper Trading",
    howBuilt: [
      "ใช้ Google Gemini 2.5 Flash พร้อม Function Calling (AI เรียกข้อมูลจาก DB เองได้)",
      "Tools ที่ AI ใช้: get_stock_analysis (วิเคราะห์หุ้น), get_us_stock_bars (ดึงราคาจาก Alpaca), propose_order (เสนอ order)",
      "ข้อมูลหุ้น US ดึงจาก Alpaca Market Data API แบบ real-time",
      "ข้อมูลหุ้นไทยดึงจาก DB (Yahoo/Stooq feed)",
    ],
    sections: [
      { title: "💬 ตัวอย่างคำถามที่ถามได้", items: [
        "วิเคราะห์ AAPL ให้หน่อย",
        "แนะนำหุ้น US น่าซื้อตอนนี้",
        "เปรียบเทียบ NVDA กับ META",
        "RSI ของ TSLA เท่าไหร่",
        "ซื้อ AAPL 10 หุ้น ราคาตลาด (Paper Trading)",
        "ดู portfolio ของฉัน",
      ]},
      { title: "📊 ข้อมูลที่ AI เข้าถึงได้", items: [
        "ราคา OHLCV ย้อนหลังจาก Alpaca (หุ้น US) และ DB (หุ้นไทย)",
        "Indicators ทั้งหมด: EMA, RSI, MACD, BB, ATR, ADX, DI+/DI−, Volume",
        "Multi-Layer Analysis: Trend, Structure, Pattern, Momentum",
        "Alpaca Account: balance, positions, order history",
      ]},
      { title: "📝 Paper Trading ผ่าน AI", items: [
        "AI เสนอ order → แสดงรายละเอียด (symbol, จำนวน, ประเภท, เหตุผล)",
        "User กดยืนยัน → ส่ง order ไป Alpaca Paper Trading API",
        "User กดยกเลิก → ไม่ส่ง order",
        "ดูประวัติ order ได้ที่ Admin > Alpaca Orders",
      ]},
    ],
  },
  {
    id: "data_source", icon: "🔗", label: "แหล่งข้อมูล", color: "#26a69a",
    purpose: "อธิบายว่าระบบดึงข้อมูลจากที่ไหน — หุ้น US จาก Alpaca, หุ้นไทยจาก Yahoo/Stooq แยกกันชัดเจน ไม่ปนกัน",
    howBuilt: [
      "หุ้น US (NASDAQ/NYSE) — ข้อมูลราคาจาก Alpaca Market Data API (IEX feed)",
      "หุ้นไทย (SET) — ข้อมูลราคาจาก Yahoo Finance / Stooq",
      "ข้อมูลถูกเก็บใน Database เดียวกัน (PriceDaily + Indicator)",
      "ทุก Indicator คำนวณจากข้อมูลเดียวกัน ไม่ว่าจะ US หรือ ไทย",
    ],
    sections: [
      { title: "🇺🇸 หุ้น US (Alpaca)", items: [
        "128 symbols (AAPL, TSLA, NVDA, META, GOOGL, AMZN ฯลฯ)",
        "ดึงราคา OHLCV ย้อนหลัง 120 วัน",
        "คำนวณ Indicators ทั้งหมด: EMA, RSI, MACD, BB, ATR, ADX, DI+/DI−, Volume Avg, S/R",
        "อัพเดททุกวัน (Celery schedule)",
        "Paper Trading ผ่าน Alpaca API",
      ]},
      { title: "🇹🇭 หุ้นไทย (Yahoo/Stooq)", items: [
        "หุ้น SET ทั้งหมดที่มีใน Database",
        "ดึงราคา OHLCV จาก Yahoo Finance / Stooq",
        "คำนวณ Indicators เหมือนกับหุ้น US",
        "ไม่มี Paper Trading (ยังไม่รองรับ)",
      ]},
      { title: "⚠️ ข้อจำกัด", items: [
        "ข้อมูลเป็น End-of-Day (ไม่ใช่ real-time ระหว่างวัน)",
        "Alpaca IEX feed มี delay 15 นาทีสำหรับ free tier",
        "Symbols ที่มี . หรือ - (เช่น BRK-B, BRK.B) ยังไม่รองรับใน Alpaca",
      ]},
    ],
  },
]

// ── Menu Guide Tab ────────────────────────────────────────────────────────────
function MenuGuideTab() {
  const [selected, setSelected] = useState<MenuItem>(MENU_GUIDE[0])

  return (
    <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16, alignItems: "start" }}>
      {/* Sidebar */}
      <div className="card" style={{ padding: "12px 8px" }}>
        <div className="card-title" style={{ paddingLeft: 8, marginBottom: 8 }}>เลือกเมนู</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {MENU_GUIDE.map(item => {
            const isActive = selected.id === item.id
            return (
              <button key={item.id}
                onClick={() => setSelected(item)}
                style={{
                  display: "flex", alignItems: "center", gap: 10,
                  padding: "9px 12px", borderRadius: 8, border: "none", cursor: "pointer",
                  background: isActive ? "var(--accent-dim)" : "transparent",
                  color: isActive ? "var(--accent)" : "var(--text-secondary)",
                  textAlign: "left", fontWeight: isActive ? 700 : 500, fontSize: 13,
                  transition: "all 0.12s",
                }}>
                <span style={{ fontSize: 16, flexShrink: 0 }}>{item.icon}</span>
                <span>{item.label}</span>
                {isActive && <span style={{ marginLeft: "auto", fontSize: 10 }}>▶</span>}
              </button>
            )
          })}
        </div>
      </div>

      {/* Detail Panel */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

        {/* Header */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 14 }}>
            <span style={{ fontSize: 36 }}>{selected.icon}</span>
            <div>
              <div style={{ fontSize: 22, fontWeight: 800, color: selected.color }}>{selected.label}</div>
            </div>
          </div>

          {/* Purpose */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
              textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
              🎯 มีไว้เพื่ออะไร
            </div>
            <p style={{ fontSize: 14, lineHeight: 1.8, color: "var(--text-primary)", margin: 0,
              padding: "12px 16px", background: "var(--bg-elevated)", borderRadius: 8,
              borderLeft: `3px solid ${selected.color}` }}>
              {selected.purpose}
            </p>
          </div>

          {/* How Built */}
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
              textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
              ⚙️ สร้างขึ้นมาอย่างไร
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {selected.howBuilt.map((line, i) => (
                <div key={i} style={{ display: "flex", gap: 10, fontSize: 13,
                  padding: "8px 12px", background: "var(--bg-elevated)", borderRadius: 7 }}>
                  <span style={{ color: selected.color, fontWeight: 700, flexShrink: 0 }}>{i + 1}.</span>
                  <span style={{ color: "var(--text-secondary)", lineHeight: 1.6 }}>{line}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* How To Use Sections */}
        <div className="card" style={{ padding: "20px 24px" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
            textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 14 }}>
            📖 ใช้อย่างไร
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {selected.sections.map((sec, si) => (
              <div key={si}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)",
                  marginBottom: 8, padding: "6px 10px",
                  background: `${selected.color}12`, borderRadius: 6,
                  borderLeft: `3px solid ${selected.color}` }}>
                  {sec.title}
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingLeft: 8 }}>
                  {sec.items.map((item, ii) => (
                    <div key={ii} style={{ display: "flex", gap: 8, fontSize: 13,
                      color: "var(--text-secondary)", lineHeight: 1.6 }}>
                      <span style={{ color: selected.color, flexShrink: 0, marginTop: 2 }}>•</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}

// ── Main Combined Page ────────────────────────────────────────────────────────
export default function Guide() {
  const [tab, setTab] = useState<"guide" | "menu">("guide")

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">💡 คำแนะนำ</div>
        <div className="page-subtitle">คู่มือ Indicator · สูตรคำนวณ · คู่มือเมนู</div>
      </div>
      <div className="page-body">

        {/* Tab nav */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
          <button style={tabStyle(tab === "guide")} onClick={() => setTab("guide")}>
            💡 คำแนะนำ Indicator
          </button>
          <button style={tabStyle(tab === "menu")} onClick={() => setTab("menu")}>
            🗺️ คู่มือเมนู
          </button>
        </div>

        {tab === "guide" && <GuideTab />}
        {tab === "menu"  && <MenuGuideTab />}

      </div>
    </div>
  )
}
