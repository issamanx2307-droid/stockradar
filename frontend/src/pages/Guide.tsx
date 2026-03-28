import { useEffect, useMemo, useRef, useState } from "react"
import { GUIDE_DATA, GuideItem } from "../data/guideData"
import { api } from "../api/client"
import { StockTermInfo } from "../api/types"
import { AiTerm, TermText } from "../components/TermAssistant"

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

// ── Q&A Tab ───────────────────────────────────────────────────────────────────
type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string; term?: StockTermInfo }

function uid() { return `${Date.now()}-${Math.random().toString(16).slice(2)}` }

function QnaTab() {
  const [featured, setFeatured] = useState<StockTermInfo[]>([])
  const [query, setQuery]       = useState("")
  const [messages, setMessages] = useState<Msg[]>([{
    id: uid(), role: "assistant",
    text: "พิมพ์ศัพท์เทคนิคหรือคำถาม เช่น RSI คืออะไร, BB Bands ใช้ยังไง",
  }])
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    api.getFeaturedTerms().then(r => setFeatured(r.results || [])).catch(() => setFeatured([]))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  const canSend = useMemo(() => query.trim().length > 0 && !busy, [query, busy])

  async function send() {
    const text = query.trim()
    if (!text || busy) return
    setQuery("")
    setBusy(true)
    setMessages(prev => [...prev, { id: uid(), role: "user", text }])
    try {
      const res = await api.askQuestion(text)
      if (res.found && res.term) {
        const term = res.term
        setMessages(prev => [...prev, {
          id: uid(), role: "assistant",
          text: term.short_definition || term.full_definition || "มีคำตอบแล้ว",
          term,
        }])
      } else {
        setMessages(prev => [...prev, {
          id: uid(), role: "assistant",
          text: res.message || "ยังไม่มีคำตอบ ระบบได้ส่งคำถามไปให้ผู้ดูแลแล้ว",
        }])
      }
    } catch {
      setMessages(prev => [...prev, { id: uid(), role: "assistant", text: "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง" }])
    } finally { setBusy(false) }
  }

  function showTerm(term: StockTermInfo) {
    setMessages(prev => [...prev, {
      id: uid(), role: "assistant",
      text: term.short_definition || term.full_definition || term.term,
      term,
    }])
  }

  return (
    <div className="qna-layout">
      <aside className="card qna-side">
        <div className="card-title">คำถาม/ศัพท์ที่พบบ่อย</div>
        <div className="qna-term-list">
          {featured.map(t => (
            <button key={t.term} className="qna-term-btn" onClick={() => showTerm(t)}>
              <div className="qna-term-code"><AiTerm token={t.term}>{t.term}</AiTerm></div>
              <div className="qna-term-desc"><TermText text={t.short_definition} /></div>
            </button>
          ))}
        </div>
      </aside>

      <section className="card qna-main">
        <div className="qna-messages">
          {messages.map(m => (
            <div key={m.id} className={`qna-msg ${m.role}`}>
              <div className="qna-bubble">
                <div className="qna-text"><TermText text={m.text} /></div>
                {"term" in m && m.term && (
                  <div className="qna-term-full">
                    <div className="qna-term-full-title"><AiTerm token={m.term.term}>{m.term.term}</AiTerm></div>
                    <div className="qna-term-full-body">{m.term.full_definition}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="qna-input">
          <input className="input-field" value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="พิมพ์ศัพท์หรือคำถาม แล้วกด Enter…"
            onKeyDown={e => { if (e.key === "Enter") send() }}
            disabled={busy} />
          <button className="btn btn-primary" onClick={send} disabled={!canSend}>ส่ง</button>
        </div>
      </section>
    </div>
  )
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
        "ทั้งหมด — ทุกสัญญาณ",
        "สัญญาณขาขึ้น 🟢 — โมเมนตัมบวก, โมเมนตัมบวกแรง, GOLDEN_CROSS, EMA Align ฯลฯ",
        "สัญญาณขาลง 🔴 — โมเมนตัมลบ, DEATH_CROSS, BREAKDOWN ฯลฯ",
        "Breakout 🚀 — หุ้นที่ราคาทะลุแนวต้านสำคัญ",
        "เฝ้าดู 👁️ — หุ้นที่น่าจับตาแต่ยังไม่ถึงจุดเข้า",
      ]},
      { title: "🎛️ Filter Bar", items: [
        "กรองตาม: ประเภทสัญญาณ / ตลาด (SET, NASDAQ, NYSE) / ช่วงเวลา / Score ขั้นต่ำ",
        "คลิกแถวหุ้นในตาราง → เปิดหน้ากราฟทันที",
        "ตาราง Signal แสดง: รหัสหุ้น, สัญญาณ, ราคา, Stop Loss, Risk %, Score Bar, เวลา",
      ]},
      { title: "🌏 Sidebar: สัญญาณตามตลาด", items: [
        "Progress bar แสดงสัดส่วนสัญญาณในแต่ละตลาด (SET / NASDAQ / NYSE)",
      ]},
    ],
  },
  {
    id: "engine_scan", icon: "🔥", label: "Top Opportunities", color: "#ff6d00",
    purpose: "ค้นหาหุ้นที่ดีที่สุดในขณะนี้โดยใช้ระบบคะแนน 5 ปัจจัย (5-Factor Scoring Engine) — ไม่ใช่แค่สัญญาณ แต่จัดอันดับว่าหุ้นไหนผ่านมากที่สุดในด้าน Trend, Momentum, Volume, Volatility และ Risk",
    howBuilt: [
      "Engine ที่ /engine/scan/ ประมวลผลหุ้นทุกตัวตามช่วงเวลาที่เลือก คำนวณ Score 0–100",
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
      "Backend ดึงข้อมูลจาก Yahoo Finance API (และจะเปลี่ยนเป็น Polygon.io)",
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
      "เรียก /engine/portfolio/ ส่ง: capital, exchange, min_score",
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
    id: "scanner", icon: "🔍", label: "สแกนหุ้น", color: "var(--green)",
    purpose: "ค้นหาหุ้นตามเงื่อนไขทางเทคนิคที่กำหนดเอง — ยืดหยุ่นกว่า Radar ตรงที่ผู้ใช้กำหนด filter ได้เอง ทั้งแบบ preset formula และแบบเขียนเองได้",
    howBuilt: [
      "Backend /api/scanner/ รับ params แล้วกรองจาก Signal Database",
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
    purpose: "สร้างกลยุทธ์การลงทุนเอง — กำหนดเงื่อนไข Indicator หลายข้อ แล้วสั่งให้ระบบสแกนว่าหุ้นไหนตรงตามกลยุทธ์นั้น",
    howBuilt: [
      "กลยุทธ์ถูกแปลงเป็น Condition Set ส่งไปที่ Backend",
      "Backend ประเมินทุกหุ้นว่าผ่านเงื่อนไข AND/OR ครบไหม",
      "มี Preset Strategy สำเร็จรูปให้เลือกได้ทันที",
    ],
    sections: [
      { title: "📚 Preset Strategies", items: [
        "⭐ MA Cross — Bullish: EMA20 > EMA50 > EMA200 + RSI > 45",
        "🔵 RSI Oversold Bounce: RSI < 30 + ราคาเหนือ EMA200",
        "📶 MACD Bullish Cross: MACD Line > Signal + MACD Hist > 0",
        "🚀 Bollinger Breakout: ราคาทะลุ BB Upper + Volume > avg",
      ]},
      { title: "🛠️ สร้างกลยุทธ์เอง", items: [
        "Indicator: EMA20/50/200, RSI, MACD, MACD Signal, MACD Hist, BB Upper/Lower, Volume",
        "Operator: > (มากกว่า), < (น้อยกว่า), >=, <=",
        "Target: Indicator อีกตัว หรือค่าตัวเลข",
        "Logic: AND (ต้องครบทุกข้อ) / OR (แค่ข้อเดียว)",
        "เพิ่มเงื่อนไขได้ไม่จำกัด",
      ]},
      { title: "▶️ Run Strategy", items: [
        "กด Run → ระบบสแกนหุ้นทุกตัวใน Database",
        "ผล: รายชื่อหุ้นที่ผ่านเงื่อนไขทั้งหมด พร้อมรายละเอียด",
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
  const [tab, setTab] = useState<"guide" | "qna" | "menu">("guide")

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">💡 คำแนะนำ & ถาม-ตอบ</div>
        <div className="page-subtitle">คู่มือ Indicator · สูตรคำนวณ · ถาม-ตอบศัพท์เทคนิค · คู่มือเมนู</div>
      </div>
      <div className="page-body">

        {/* Tab nav */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button style={tabStyle(tab === "guide")} onClick={() => setTab("guide")}>
            💡 คำแนะนำ Indicator
          </button>
          <button style={tabStyle(tab === "qna")} onClick={() => setTab("qna")}>
            💬 ถาม-ตอบศัพท์เทคนิค
          </button>
          <button style={tabStyle(tab === "menu")} onClick={() => setTab("menu")}>
            🗺️ คู่มือเมนู
          </button>
        </div>

        {tab === "guide" && <GuideTab />}
        {tab === "qna"   && <QnaTab />}
        {tab === "menu"  && <MenuGuideTab />}

      </div>
    </div>
  )
}
