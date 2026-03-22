/**
 * pages/EngineBacktest.tsx
 * Backtest ด้วย Engine ใหม่ — equity curve + metrics report
 */
import { useState, useEffect, useRef } from "react"
import { engineApi, BacktestResult } from "../api/engineApi"
import { createChart, LineSeries } from "lightweight-charts"

function EquityChart({ equity }: { equity: number[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current || !equity.length) return
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth, height: 240,
      layout: { background: { color: "#111827" }, textColor: "#7a90a8" },
      grid: { vertLines: { color: "#1e2d42" }, horzLines: { color: "#1e2d42" } },
      rightPriceScale: { borderColor: "#1e2d42" },
      timeScale: { borderColor: "#1e2d42", timeVisible: false },
    })
    const series = chart.addSeries(LineSeries, {
      color: "#00e676", lineWidth: 2, title: "Equity"
    })
    series.setData(equity.map((v, i) => ({ time: (i + 1) as any, value: v })))
    chart.timeScale().fitContent()
    const ro = new ResizeObserver(() => chart.applyOptions({ width: ref.current?.clientWidth || 0 }))
    ro.observe(ref.current)
    return () => { chart.remove(); ro.disconnect() }
  }, [equity])
  return <div ref={ref} style={{ width: "100%", height: 240 }} />
}

export default function EngineBacktest({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [symbol, setSymbol]   = useState("")
  const [capital, setCapital] = useState(100000)
  const [slPct, setSlPct]     = useState(5)
  const [tpPct, setTpPct]     = useState(10)
  const [days, setDays]       = useState(730)
  const [result, setResult]   = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState("")

  async function handleRun() {
    if (!symbol.trim()) return
    setLoading(true); setError(""); setResult(null)
    try {
      const res = await engineApi.backtest({
        symbol: symbol.trim().toUpperCase(),
        capital, stop_loss_pct: slPct, take_profit_pct: tpPct, days
      })
      setResult(res)
    } catch (e: any) {
      setError(e.message || "Backtest ล้มเหลว")
    }
    setLoading(false)
  }

  const m = result?.metrics
  const r = result?.report

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">⏪ Backtest Engine</div>
        <div className="page-subtitle">ทดสอบกลยุทธ์บนข้อมูลย้อนหลัง · Equity Curve · Sharpe</div>
      </div>
      <div className="page-body">

        {/* ── Settings ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>รหัสหุ้น</div>
              <input className="filter-input" placeholder="PTT, AAPL..." value={symbol}
                onChange={e => setSymbol(e.target.value.toUpperCase())}
                onKeyDown={e => e.key === "Enter" && handleRun()}
                style={{ width: 120, fontFamily: "var(--font-mono)", fontWeight: 700 }} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>เงินทุน</div>
              <input className="filter-input" type="number" value={capital}
                onChange={e => setCapital(Number(e.target.value))}
                style={{ width: 130, fontFamily: "var(--font-mono)" }} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>Stop Loss %</div>
              <input className="filter-input" type="number" value={slPct}
                onChange={e => setSlPct(Number(e.target.value))}
                style={{ width: 80, fontFamily: "var(--font-mono)" }} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>Take Profit %</div>
              <input className="filter-input" type="number" value={tpPct}
                onChange={e => setTpPct(Number(e.target.value))}
                style={{ width: 80, fontFamily: "var(--font-mono)" }} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>ช่วงเวลา</div>
              <div style={{ display: "flex", gap: 4 }}>
                {[{ l: "1 ปี", v: 365 }, { l: "2 ปี", v: 730 }, { l: "5 ปี", v: 1825 }].map(d => (
                  <button key={d.v} onClick={() => setDays(d.v)} style={{
                    padding: "6px 10px", borderRadius: 6, fontSize: 12, cursor: "pointer",
                    border: `1px solid ${days === d.v ? "var(--accent)" : "var(--border)"}`,
                    background: days === d.v ? "var(--accent-dim)" : "transparent",
                    color: days === d.v ? "var(--accent)" : "var(--text-muted)", fontWeight: 600,
                  }}>{d.l}</button>
                ))}
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleRun}
              disabled={loading} style={{ height: 38, minWidth: 120 }}>
              {loading ? "⏳ กำลังคำนวณ..." : "▶ รัน Backtest"}
            </button>
            {result && onOpenChart && (
              <button className="btn btn-ghost" onClick={() => onOpenChart(result.symbol)}
                style={{ height: 38 }}>📈 ดูกราฟ</button>
            )}
          </div>
          {error && <div style={{ marginTop: 10, color: "var(--red)", fontSize: 13 }}>❌ {error}</div>}
        </div>

        {result && m && r && (
          <>
            {/* ── Metrics ── */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
              {[
                { label: "Total Return",   val: r["Total Return"],   color: parseFloat(String(r["Total Return"])) >= 0 ? "var(--green)" : "var(--red)" },
                { label: "Win Rate",       val: r["Win Rate"],       color: "var(--accent)" },
                { label: "Max Drawdown",   val: r["Max Drawdown"],   color: "var(--red)" },
                { label: "Sharpe Ratio",   val: r["Sharpe Ratio"],   color: Number(r["Sharpe Ratio"]) >= 1 ? "var(--green)" : "var(--yellow)" },
                { label: "Profit Factor",  val: r["Profit Factor"],  color: "var(--text-primary)" },
                { label: "Total Trades",   val: r["Total Trades"],   color: "var(--text-primary)" },
                { label: "Winning Trades", val: r["Winning Trades"], color: "var(--green)" },
                { label: "Final Equity",   val: `฿${r["Final Equity"]}`, color: "var(--accent)" },
              ].map(({ label, val, color }) => (
                <div key={label} className="card" style={{ textAlign: "center", padding: "12px 8px" }}>
                  <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color }}>{val}</div>
                </div>
              ))}
            </div>

            {/* ── Equity Curve ── */}
            <div className="card" style={{ marginBottom: 20, padding: 0, overflow: "hidden" }}>
              <div style={{ padding: "14px 16px 8px" }} className="card-title">
                📈 Equity Curve — {result.symbol}
              </div>
              <EquityChart equity={result.equity_curve} />
            </div>

            {/* ── Performance Analysis ── */}
            <div className="card">
              <div className="card-title">🧮 วิเคราะห์ผลลัพธ์</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {[
                  {
                    label: "คะแนน Sharpe",
                    val: Number(r["Sharpe Ratio"]),
                    text: Number(r["Sharpe Ratio"]) >= 2 ? "ดีเยี่ยม (≥2.0)" :
                          Number(r["Sharpe Ratio"]) >= 1 ? "ดี (1.0–2.0)" :
                          Number(r["Sharpe Ratio"]) >= 0 ? "พอใช้ (0–1.0)" : "ไม่ดี (<0)",
                    color: Number(r["Sharpe Ratio"]) >= 1 ? "var(--green)" : Number(r["Sharpe Ratio"]) >= 0 ? "var(--yellow)" : "var(--red)"
                  },
                  {
                    label: "Win Rate",
                    val: m.win_rate * 100,
                    text: m.win_rate >= 0.6 ? "ชนะบ่อย (≥60%)" :
                          m.win_rate >= 0.5 ? "พอดี (50–60%)" : "แพ้บ่อย (<50%)",
                    color: m.win_rate >= 0.5 ? "var(--green)" : "var(--red)"
                  },
                  {
                    label: "Max Drawdown",
                    val: Math.abs(m.max_drawdown * 100),
                    text: Math.abs(m.max_drawdown) <= 0.10 ? "เสี่ยงต่ำ (≤10%)" :
                          Math.abs(m.max_drawdown) <= 0.20 ? "เสี่ยงปานกลาง (10–20%)" : "เสี่ยงสูง (>20%)",
                    color: Math.abs(m.max_drawdown) <= 0.10 ? "var(--green)" :
                           Math.abs(m.max_drawdown) <= 0.20 ? "var(--yellow)" : "var(--red)"
                  },
                ].map(({ label, val, text, color }) => (
                  <div key={label} style={{ display: "flex", alignItems: "center", gap: 12,
                    borderBottom: "1px solid var(--border)", paddingBottom: 10 }}>
                    <div style={{ width: 120, fontSize: 12, color: "var(--text-muted)" }}>{label}</div>
                    <div style={{ flex: 1, height: 6, background: "var(--border)", borderRadius: 3 }}>
                      <div style={{ width: `${Math.min(val, 100)}%`, height: "100%",
                        background: color, borderRadius: 3, transition: "width 0.6s" }} />
                    </div>
                    <div style={{ fontSize: 12, fontWeight: 700, color, minWidth: 180 }}>{text}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {!result && !loading && (
          <div className="empty-state">
            <span style={{ fontSize: 48 }}>⏪</span>
            <span style={{ fontWeight: 600 }}>ใส่รหัสหุ้นแล้วกด "รัน Backtest"</span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              ทดสอบกลยุทธ์ 5-Factor บนข้อมูลย้อนหลัง 1–5 ปี
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
