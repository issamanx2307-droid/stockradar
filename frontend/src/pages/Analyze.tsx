/**
 * pages/Analyze.tsx
 * วิเคราะห์หุ้นเดียวด้วย Engine ใหม่
 * Score breakdown 5 หมวด + reasons + entry/stop/size
 */
import { useState } from "react"
import { engineApi, EngineResult } from "../api/engineApi"
import DecisionBadge from "../components/DecisionBadge"
import ScoreCard from "../components/ScoreCard"

const BREAKDOWN_CONFIG = [
  { key: "trend",      label: "📈 Trend",      max: 40, color: "#00d4ff" },
  { key: "momentum",   label: "🚀 Momentum",   max: 25, color: "#ffd740" },
  { key: "volume",     label: "📢 Volume",     max: 15, color: "#69f0ae" },
  { key: "volatility", label: "⚡ Volatility", max: 10, color: "#ce93d8" },
]

export default function Analyze({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [symbol, setSymbol]   = useState("")
  const [capital, setCapital] = useState(100000)
  const [data, setData]       = useState<EngineResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState("")

  async function handleAnalyze() {
    if (!symbol.trim()) return
    setLoading(true); setError(""); setData(null)
    try {
      const res = await engineApi.analyze(symbol.trim().toUpperCase(), capital)
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
              <input className="filter-input" placeholder="PTT, KBANK, AAPL..."
                value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())}
                onKeyDown={e => e.key === "Enter" && handleAnalyze()}
                style={{ width: "100%", fontFamily: "var(--font-mono)", fontWeight: 700 }} />
            </div>
            <div style={{ minWidth: 160 }}>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>เงินทุน (บาท)</div>
              <input className="filter-input" type="number" value={capital}
                onChange={e => setCapital(Number(e.target.value))}
                style={{ width: "100%", fontFamily: "var(--font-mono)" }} />
            </div>
            <button className="btn btn-primary" onClick={handleAnalyze}
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
              <div style={{ fontFamily: "var(--font-mono)", fontSize: 28, fontWeight: 700 }}>
                {typeof data.score === "number" ? data.score : (data as any).score?.total_score}
                <span style={{ fontSize: 14, color: "var(--text-muted)" }}>/100</span>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

              {/* ── Score Breakdown ── */}
              <div className="card">
                <div className="card-title">📊 Score Breakdown</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                  {BREAKDOWN_CONFIG.map(({ key, label, max, color }) => {
                    const val = bd[key] ?? 0
                    const pct = (val / max) * 100
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
                      </div>
                    )
                  })}
                  {(bd.risk_penalty ?? 0) > 0 && (
                    <div style={{ fontSize: 12, color: "var(--red)",
                      background: "rgba(255,82,82,0.08)", borderRadius: 6, padding: "6px 10px" }}>
                      ⚠️ Risk Penalty: −{bd.risk_penalty} คะแนน
                    </div>
                  )}
                </div>
              </div>

              {/* ── Trade Setup ── */}
              <div className="card">
                <div className="card-title">💰 Trade Setup</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {[
                    { label: "Entry",         val: data.entry?.toLocaleString("th-TH", { minimumFractionDigits: 2 }),  color: "var(--green)"  },
                    { label: "Stop Loss",     val: data.stop_loss?.toLocaleString("th-TH", { minimumFractionDigits: 2 }), color: "var(--red)" },
                    { label: "Risk %",        val: `${data.risk_pct}%`, color: "var(--yellow)" },
                    { label: "Position Size", val: `${data.size?.toLocaleString() ?? "-"} หุ้น`, color: "var(--accent)" },
                    { label: "ต้นทุน",        val: data.size && data.entry
                        ? `฿${(data.size * data.entry).toLocaleString("th-TH", { maximumFractionDigits: 0 })}`
                        : "-", color: "var(--text-primary)" },
                    { label: "RSI 14",        val: data.rsi?.toFixed(1) ?? "-",  color: "var(--blue)"   },
                    { label: "ADX 14",        val: data.adx?.toFixed(1) ?? "-",  color: "var(--purple, #ce93d8)" },
                  ].map(({ label, val, color }) => (
                    <div key={label} style={{ display: "flex", justifyContent: "space-between",
                      fontSize: 13, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
                      <span style={{ color: "var(--text-muted)" }}>{label}</span>
                      <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color }}>{val}</span>
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
