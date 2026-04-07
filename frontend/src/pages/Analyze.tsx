/**
 * pages/Analyze.tsx
 * วิเคราะห์หุ้นเดียวด้วย Engine ใหม่
 * Score breakdown 5 หมวด + reasons + entry/stop/size
 */
import { useState, useRef, useEffect } from "react"
import { engineApi, EngineResult } from "../api/engineApi"
import DecisionBadge from "../components/DecisionBadge"
import ScoreCard from "../components/ScoreCard"
import SymbolInput from "../components/SymbolInput"

const BREAKDOWN_CONFIG = [
  { key: "trend",      label: "📈 Trend",      max: 40, color: "#00d4ff" },
  { key: "momentum",   label: "🚀 Momentum",   max: 25, color: "#ffd740" },
  { key: "volume",     label: "📢 Volume",     max: 15, color: "#69f0ae" },
  { key: "volatility", label: "⚡ Volatility", max: 10, color: "#ce93d8" },
]

export default function Analyze({ onOpenChart, initialSymbol }: {
  onOpenChart?: (s: string) => void
  initialSymbol?: string | null
}) {
  const [symbol, setSymbol]   = useState(initialSymbol || "")
  const [capital, setCapital] = useState(100000)
  const [data, setData]       = useState<EngineResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState("")
  // ref เก็บค่า symbol ล่าสุดเสมอ — แก้ closure bug ใน onSelect
  const symRef = useRef(initialSymbol || "")

  // ถ้ามี initialSymbol → วิเคราะห์ทันที
  useEffect(() => {
    if (initialSymbol) {
      symRef.current = initialSymbol
      handleAnalyze(initialSymbol)
    }
  }, [])

  function handleSymbolChange(v: string) {
    setSymbol(v)
    symRef.current = v
  }

  async function handleAnalyze(overrideSym?: string) {
    // overrideSym มาจาก dropdown click — ใช้ตรงนี้เลยไม่รอ state update
    const sym = (overrideSym ?? symRef.current).trim().toUpperCase()
    if (!sym) return
    if (overrideSym) { setSymbol(overrideSym); symRef.current = overrideSym }
    setLoading(true); setError(""); setData(null)
    try {
      const res = await engineApi.analyze(sym, capital)
      setData(res)
    } catch (e: any) {
      setError(e.message || "วิเคราะห์ไม่สำเร็จ")
    }
    setLoading(false)
  }

  const bd = data?.breakdown as any ?? {}

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">🔬 วิเคราะห์หุ้น</div>
        <div className="page-subtitle">Score 5 หมวด · Entry · Stop Loss · Position Size</div>
      </div>
      <div className="page-body">

        {/* ── Input ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div style={{ flex: 1, minWidth: 180 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>รหัสหุ้น</div>
              <SymbolInput
                value={symbol} onChange={handleSymbolChange} onSelect={handleAnalyze}
                placeholder="PTT, KBANK, AAPL..." />
            </div>
            <div style={{ minWidth: 160 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>เงินทุน (บาท)</div>
              <input className="filter-input" type="number" value={capital}
                onChange={e => setCapital(Number(e.target.value))}
                style={{ width: "100%", fontFamily: "var(--font-mono)" }} />
            </div>
            <button className="btn btn-primary" onClick={() => handleAnalyze()}
              disabled={loading} style={{ height: 38, minWidth: 120 }}>
              {loading ? "⏳ กำลังวิเคราะห์..." : "🔬 วิเคราะห์"}
            </button>
            {data && onOpenChart && (
              <button className="btn btn-ghost" onClick={() => onOpenChart(data.symbol)}
                style={{ height: 38 }}>📈 ดูกราฟ</button>
            )}
          </div>
          {error && <div style={{ marginTop: 10, color: "var(--red)", fontSize: 13 }}>❌ {error}</div>}
        </div>

        {data && (
          <>
            {/* ── Header ── */}
            <div style={{ display: "flex", gap: 16, alignItems: "center",
              marginBottom: 20, flexWrap: "wrap" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 32, fontWeight: 700 }}>
                {data.symbol}
              </span>
              <DecisionBadge decision={data.decision} />
              {(() => {
                const sc = typeof data.score === "number" ? data.score : ((data as any).score?.total_score ?? 0)
                const color = sc>=80?"#00c853":sc>=60?"var(--green)":sc>=40?"var(--yellow)":"var(--red)"
                const grade = sc>=80?"ดีมาก":sc>=60?"ดี":sc>=40?"พอใช้":"อ่อน"
                return (
                  <div style={{ display:"flex", alignItems:"baseline", gap:8 }}>
                    <span style={{ fontFamily:"var(--font-mono)", fontSize:28, fontWeight:700, color }}>
                      {sc}<span style={{ fontSize:14, color:"var(--text-muted)" }}>/100</span>
                    </span>
                    <span style={{ fontSize:13, fontWeight:700, padding:"3px 10px", borderRadius:6,
                      background:`${color}22`, color }}>
                      {sc>=80?"⭐ ":sc>=60?"✅ ":sc>=40?"⚠️ ":"❌ "}{grade}
                    </span>
                  </div>
                )
              })()}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

              {/* ── Score Breakdown ── */}
              <div className="card">
                <div className="card-title">📊 Score Breakdown</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {BREAKDOWN_CONFIG.map(({ key, label, max, color }) => {
                    const val = bd[key] ?? 0
                    const pct = (val / max) * 100
                    // threshold hints per dimension
                    const hints: Record<string,string> = {
                      trend:      "ดีมาก ≥30 · ดี ≥20 · อ่อน <15",
                      momentum:   "ดีมาก ≥18 · ดี ≥12 · อ่อน <8",
                      volume:     "ดีมาก ≥10 · ดี ≥7 · อ่อน <5",
                      volatility: "ดีมาก ≥7 · ดี ≥5 · อ่อน <3",
                    }
                    return (
                      <div key={key}>
                        <div style={{ display: "flex", justifyContent: "space-between",
                          fontSize: 12, marginBottom: 4 }}>
                          <span>{label}</span>
                          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color }}>
                            {val} / {max}
                          </span>
                        </div>
                        <div style={{ height: 8, background: "var(--border)", borderRadius: 4 }}>
                          <div style={{ width: `${pct}%`, height: "100%", background: color,
                            borderRadius: 4, transition: "width 0.6s ease" }} />
                        </div>
                        <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
                          {hints[key]}
                        </div>
                      </div>
                    )
                  })}
                  {(bd.risk_penalty ?? 0) > 0 && (
                    <div style={{ fontSize: 12, color: "var(--red)",
                      background: "rgba(255,82,82,0.08)", borderRadius: 6, padding: "6px 10px" }}>
                      ⚠️ Risk Penalty: −{bd.risk_penalty} คะแนน (หักเมื่อ Risk % สูงเกิน)
                    </div>
                  )}
                </div>
              </div>

              {/* ── Trade Setup ── */}
              <div className="card">
                <div className="card-title">💰 Trade Setup</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {[
                    { label: "Entry",         val: data.entry?.toLocaleString("th-TH", { minimumFractionDigits: 2 }),  color: "var(--green)",  hint: "ราคาที่เหมาะสมในการเข้าซื้อ" },
                    { label: "Stop Loss",     val: data.stop_loss?.toLocaleString("th-TH", { minimumFractionDigits: 2 }), color: "var(--red)", hint: "ราคาตัดขาดทุน — ออกทันทีเมื่อหลุดระดับนี้" },
                    { label: "Risk %",        val: `${data.risk_pct}%`, color: (data.risk_pct??0)<=2?"var(--green)":(data.risk_pct??0)<=5?"var(--yellow)":"var(--red)", hint: "ดี ≤2% · พอใช้ ≤5% · สูง >5% ต่อ trade" },
                    { label: "Position Size", val: `${data.size?.toLocaleString() ?? "-"} หุ้น`, color: "var(--accent)", hint: "จำนวนหุ้นที่แนะนำตามเงินทุนที่กรอก" },
                    { label: "ต้นทุน",        val: data.size && data.entry
                        ? `฿${(data.size * data.entry).toLocaleString("th-TH", { maximumFractionDigits: 0 })}`
                        : "-", color: "var(--text-primary)", hint: "เงินที่ใช้ซื้อ = ราคา × จำนวนหุ้น" },
                    { label: "RSI 14",        val: data.rsi?.toFixed(1) ?? "-",  color: "var(--blue)",  hint: ">70 Overbought · 50–70 Bullish · 30–50 Neutral · <30 Oversold" },
                    { label: "ADX 14",        val: data.adx?.toFixed(1) ?? "-",  color: "var(--purple, #ce93d8)", hint: ">25 มีแนวโน้มแข็งแกร่ง · 20–25 เริ่มมีแนวโน้ม · <20 Sideways" },
                  ].map(({ label, val, color, hint }) => (
                    <div key={label} style={{ borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                        <span style={{ color: "var(--text-muted)" }}>{label}</span>
                        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color }}>{val}</span>
                      </div>
                      <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>{hint}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ── Reasons ── */}
            {data.reasons && data.reasons.length > 0 && (
              <div className="card" style={{ marginTop: 20 }}>
                <div className="card-title">📋 เหตุผลการวิเคราะห์</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {data.reasons.map((r, i) => (
                    <div key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start",
                      fontSize: 13, padding: "6px 0",
                      borderBottom: i < data.reasons.length - 1 ? "1px solid var(--border)" : "none" }}>
                      <span style={{ flexShrink: 0, width: 20, height: 20, borderRadius: "50%",
                        background: "var(--accent-dim)", color: "var(--accent)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 10, fontWeight: 700 }}>{i + 1}</span>
                      <span>{r}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
