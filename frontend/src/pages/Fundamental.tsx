/**
 * pages/Fundamental.tsx
 * ข้อมูล Fundamental — P/E, EPS, งบการเงิน, Analyst Consensus
 */
import { useState, useCallback } from "react"
import SymbolInput from "../components/SymbolInput"
import { API_BASE } from "../api/config"

const BASE = API_BASE

type FundData = {
  symbol: string; ticker: string; name: string; sector: string; industry: string
  country: string; description: string; employees: number | null
  pe_trailing: number|null; pe_forward: number|null; eps: number|null
  pb_ratio: number|null; ps_ratio: number|null; peg_ratio: number|null
  ev_ebitda: number|null; market_cap: number|null; market_cap_fmt: string|null
  dividend_yield: number|null; dividend_rate: number|null; payout_ratio: number|null
  revenue: number|null; revenue_fmt: string|null
  gross_profit: number|null; net_income: number|null; net_income_fmt: string|null
  profit_margin: number|null; gross_margin: number|null; operating_margin: number|null
  ebitda_fmt: string|null; roe: number|null; roa: number|null
  revenue_growth: number|null; earnings_growth: number|null
  debt_to_equity: number|null; current_ratio: number|null; quick_ratio: number|null
  operating_cf_fmt: string|null; free_cf_fmt: string|null
  week52_high: number|null; week52_low: number|null; week52_change: number|null
  analyst_count: number|null; target_mean_price: number|null
  target_high_price: number|null; target_low_price: number|null
  recommendation: string
  analyst_summary: Record<string,number>
  quarterly_financials: Array<{period:string; revenue:number|null; gross_profit:number|null; net_income:number|null}>
  fetched_at: string; error?: string
}

// ── helpers ──────────────────────────────────────────────────────────────────
function pct(v: number|null, good = true) {
  if (v == null) return <span style={{ color:"var(--text-muted)" }}>—</span>
  const color = good ? (v >= 0 ? "var(--green)" : "var(--red)") : (v <= 0 ? "var(--green)" : "var(--red)")
  return <span style={{ color, fontWeight:700, fontFamily:"var(--font-mono)" }}>{v >= 0 ? "+" : ""}{v.toFixed(2)}%</span>
}
function num(v: number|null|string, suffix="") {
  if (v == null) return <span style={{ color:"var(--text-muted)" }}>—</span>
  return <span style={{ fontFamily:"var(--font-mono)", fontWeight:600 }}>{v}{suffix}</span>
}
function thb(v: number|null) {
  if (v == null) return <span style={{ color:"var(--text-muted)" }}>—</span>
  return <span style={{ fontFamily:"var(--font-mono)", fontWeight:600 }}>
    {v.toLocaleString("th-TH",{minimumFractionDigits:2})}
  </span>
}
function MetricRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display:"flex", justifyContent:"space-between", padding:"6px 0",
      borderBottom:"1px solid var(--border)", fontSize:13 }}>
      <span style={{ color:"var(--text-muted)" }}>{label}</span>
      <span>{value}</span>
    </div>
  )
}
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card" style={{ marginBottom:16 }}>
      <div className="card-title">{title}</div>
      {children}
    </div>
  )
}

// ── Analyst Consensus Chart ───────────────────────────────────────────────────
function AnalystChart({ summary, recommendation, count, target, current }:
  { summary: Record<string,number>; recommendation: string; count: number|null
    target: number|null; current?: number|null }) {

  const total = Object.values(summary).reduce((a,b) => a+b, 0)
  const items = [
    { key:"strongBuy",  label:"Strong Buy", color:"#00c853" },
    { key:"buy",        label:"Buy",        color:"#00e676" },
    { key:"hold",       label:"Hold",       color:"#ffd600" },
    { key:"sell",       label:"Sell",       color:"#ff7043" },
    { key:"strongSell", label:"Strong Sell",color:"#ff5252" },
  ]

  const REC_COLOR: Record<string,string> = {
    BUY:"var(--green)", STRONG_BUY:"#00c853", HOLD:"var(--yellow)",
    SELL:"var(--red)", UNDERPERFORM:"var(--red)", OUTPERFORM:"var(--green)"
  }

  return (
    <div>
      <div style={{ display:"flex", gap:12, marginBottom:12, alignItems:"center" }}>
        <div style={{ fontSize:24, fontWeight:700, color: REC_COLOR[recommendation] || "var(--accent)" }}>
          {recommendation || "—"}
        </div>
        <div style={{ fontSize:12, color:"var(--text-muted)" }}>
          จาก {count || 0} นักวิเคราะห์
        </div>
        {target && (
          <div style={{ marginLeft:"auto", textAlign:"right" }}>
            <div style={{ fontSize:11, color:"var(--text-muted)" }}>ราคาเป้าหมาย</div>
            <div style={{ fontFamily:"var(--font-mono)", fontWeight:700, fontSize:18, color:"var(--accent)" }}>
              {target.toLocaleString("th-TH",{minimumFractionDigits:2})}
            </div>
          </div>
        )}
      </div>

      {/* Stacked bar */}
      {total > 0 && (
        <>
          <div style={{ display:"flex", height:10, borderRadius:5, overflow:"hidden", gap:1, marginBottom:8 }}>
            {items.map(({ key, color }) => {
              const v = summary[key] || 0
              return v > 0 ? (
                <div key={key} style={{ flex:v, background:color, transition:"flex .4s" }} title={`${key}: ${v}`} />
              ) : null
            })}
          </div>
          <div style={{ display:"flex", gap:10, flexWrap:"wrap" }}>
            {items.map(({ key, label, color }) => {
              const v = summary[key] || 0
              return v > 0 ? (
                <div key={key} style={{ display:"flex", alignItems:"center", gap:4, fontSize:11 }}>
                  <div style={{ width:8, height:8, borderRadius:2, background:color }} />
                  <span style={{ color:"var(--text-secondary)" }}>{label}</span>
                  <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, color }}>{v}</span>
                </div>
              ) : null
            })}
          </div>
        </>
      )}
    </div>
  )
}

// ── Quarterly Bar Chart ───────────────────────────────────────────────────────
function QuarterlyChart({ data }: { data: FundData["quarterly_financials"] }) {
  if (!data || data.length === 0) return <div style={{ color:"var(--text-muted)", fontSize:13 }}>ไม่มีข้อมูล</div>

  const maxVal = Math.max(...data.flatMap(d => [d.revenue||0, d.gross_profit||0, d.net_income||0]))

  const fmt = (v: number|null) => {
    if (!v) return "—"
    if (Math.abs(v) >= 1e9) return `${(v/1e9).toFixed(1)}B`
    if (Math.abs(v) >= 1e6) return `${(v/1e6).toFixed(0)}M`
    return v.toLocaleString()
  }

  return (
    <div style={{ overflowX:"auto" }}>
      <div style={{ display:"grid", gridTemplateColumns:`repeat(${data.length},1fr)`, gap:12, minWidth:400 }}>
        {[...data].reverse().map((q, i) => (
          <div key={i} style={{ textAlign:"center" }}>
            <div style={{ fontSize:10, color:"var(--text-muted)", marginBottom:8 }}>
              {q.period?.slice(0,7) || `Q${i+1}`}
            </div>
            <div style={{ display:"flex", gap:3, height:100, alignItems:"flex-end", justifyContent:"center" }}>
              {[
                { val:q.revenue,      color:"#00d4ff", label:"Rev" },
                { val:q.gross_profit, color:"#69f0ae", label:"GP"  },
                { val:q.net_income,   color: (q.net_income||0)>=0?"#ffd740":"#ff5252", label:"NI" },
              ].map(({ val, color, label }) => {
                const h = maxVal > 0 && val ? Math.max((val/maxVal)*90, 4) : 2
                return (
                  <div key={label} style={{ display:"flex", flexDirection:"column", alignItems:"center", gap:2 }}>
                    <div style={{ fontSize:9, color:"var(--text-muted)" }}>{fmt(val)}</div>
                    <div style={{ width:20, height:`${h}px`, background:color, borderRadius:"3px 3px 0 0",
                      transition:"height .4s" }} title={`${label}: ${fmt(val)}`} />
                    <div style={{ fontSize:9, color:"var(--text-muted)" }}>{label}</div>
                  </div>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Fundamental({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [symbol, setSymbol] = useState("")
  const [data, setData]     = useState<FundData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState("")

  const load = useCallback(async (sym: string) => {
    if (!sym.trim()) return
    setLoading(true); setError(""); setData(null)
    try {
      const res = await fetch(`${BASE}/fundamental/${sym.trim().toUpperCase()}/`)
      const d   = await res.json()
      if (d.error) setError(d.error)
      else setData(d)
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📊 Fundamental Analysis</div>
        <div className="page-subtitle">P/E · EPS · งบการเงิน · Analyst Consensus · ข้อมูลจาก yfinance</div>
      </div>
      <div className="page-body">

        {/* Search */}
        <div className="card" style={{ marginBottom:20 }}>
          <div style={{ display:"flex", gap:10, alignItems:"center" }}>
            <SymbolInput
              value={symbol} onChange={setSymbol}
              onSelect={s => load(s)}
              placeholder="รหัสหุ้น — PTT, KBANK, AAPL..."
              style={{ flex:1 }} />
            <button className="btn btn-primary" onClick={() => load(symbol)}
              disabled={loading} style={{ minWidth:120, height:40 }}>
              {loading ? "⏳ กำลังโหลด..." : "🔍 ค้นหา"}
            </button>
            {data && onOpenChart && (
              <button className="btn btn-ghost" onClick={() => onOpenChart(data.symbol)}
                style={{ height:40 }}>📈 กราฟ</button>
            )}
          </div>
          {error && <div style={{ color:"var(--red)", fontSize:13, marginTop:8 }}>❌ {error}</div>}
          <div style={{ fontSize:11, color:"var(--text-muted)", marginTop:6 }}>
            ข้อมูลจาก yfinance · Cache 24 ชั่วโมง · หุ้น SET ต้องใส่ชื่อ เช่น PTT, KBANK, AAPL
          </div>
        </div>

        {loading && <div className="loading-state"><div className="loading-spinner"/><span>กำลังดึงข้อมูล fundamental...</span></div>}

        {data && !data.error && (
          <>
            {/* Header */}
            <div style={{ marginBottom:20 }}>
              <div style={{ display:"flex", alignItems:"flex-start", gap:16, flexWrap:"wrap" }}>
                <div>
                  <div style={{ fontFamily:"var(--font-mono)", fontSize:28, fontWeight:700, color:"var(--accent)" }}>
                    {data.symbol}
                  </div>
                  <div style={{ fontSize:16, fontWeight:600, marginTop:2 }}>{data.name}</div>
                  <div style={{ fontSize:13, color:"var(--text-muted)", marginTop:2 }}>
                    {data.sector} · {data.industry} · {data.country}
                  </div>
                </div>
                <div style={{ marginLeft:"auto", textAlign:"right" }}>
                  <div style={{ fontSize:11, color:"var(--text-muted)" }}>Market Cap</div>
                  <div style={{ fontFamily:"var(--font-mono)", fontSize:22, fontWeight:700, color:"var(--green)" }}>
                    {data.market_cap_fmt || "—"}
                  </div>
                </div>
              </div>
              {data.description && (
                <div style={{ fontSize:12, color:"var(--text-secondary)", marginTop:10,
                  lineHeight:1.7, padding:"10px 14px", background:"var(--bg-elevated)",
                  borderRadius:8, borderLeft:"3px solid var(--accent)" }}>
                  {data.description}
                  {data.description.length >= 400 ? "..." : ""}
                </div>
              )}
            </div>

            {/* Grid 3 คอลัมน์ */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:16 }}>

              {/* ── Valuation ── */}
              <Section title="💰 Valuation">
                <MetricRow label="P/E (Trailing)" value={num(data.pe_trailing, "x")} />
                <MetricRow label="P/E (Forward)"  value={num(data.pe_forward,  "x")} />
                <MetricRow label="P/B Ratio"       value={num(data.pb_ratio,   "x")} />
                <MetricRow label="P/S Ratio"       value={num(data.ps_ratio,   "x")} />
                <MetricRow label="PEG Ratio"       value={num(data.peg_ratio,  "x")} />
                <MetricRow label="EV/EBITDA"       value={num(data.ev_ebitda,  "x")} />
                <MetricRow label="EPS"             value={num(data.eps)} />
                <MetricRow label="Dividend Yield"  value={<span style={{ color:"var(--green)", fontFamily:"var(--font-mono)", fontWeight:700 }}>{data.dividend_yield != null ? `${data.dividend_yield.toFixed(2)}%` : "—"}</span>} />
                <MetricRow label="Payout Ratio"    value={num(data.payout_ratio, "%")} />
              </Section>

              {/* ── Profitability ── */}
              <Section title="📈 Profitability">
                <MetricRow label="Revenue"          value={num(data.revenue_fmt)} />
                <MetricRow label="Net Income"       value={num(data.net_income_fmt)} />
                <MetricRow label="EBITDA"           value={num(data.ebitda_fmt)} />
                <MetricRow label="Gross Margin"     value={pct(data.gross_margin)} />
                <MetricRow label="Operating Margin" value={pct(data.operating_margin)} />
                <MetricRow label="Net Margin"       value={pct(data.profit_margin)} />
                <MetricRow label="ROE"              value={pct(data.roe)} />
                <MetricRow label="ROA"              value={pct(data.roa)} />
                <MetricRow label="Revenue Growth"   value={pct(data.revenue_growth)} />
                <MetricRow label="Earnings Growth"  value={pct(data.earnings_growth)} />
              </Section>

              {/* ── Financial Health ── */}
              <Section title="🏦 Financial Health">
                <MetricRow label="Debt/Equity"   value={num(data.debt_to_equity, "x")} />
                <MetricRow label="Current Ratio" value={<span style={{ color: (data.current_ratio||0) >= 1 ? "var(--green)" : "var(--red)", fontFamily:"var(--font-mono)", fontWeight:700 }}>{data.current_ratio ?? "—"}</span>} />
                <MetricRow label="Quick Ratio"   value={<span style={{ color: (data.quick_ratio||0) >= 1 ? "var(--green)" : "var(--red)", fontFamily:"var(--font-mono)", fontWeight:700 }}>{data.quick_ratio ?? "—"}</span>} />
                <MetricRow label="Operating CF"  value={num(data.operating_cf_fmt)} />
                <MetricRow label="Free CF"       value={num(data.free_cf_fmt)} />
                <MetricRow label="52W High"      value={thb(data.week52_high)} />
                <MetricRow label="52W Low"       value={thb(data.week52_low)} />
                <MetricRow label="52W Change"    value={pct(data.week52_change)} />
                {data.employees && <MetricRow label="พนักงาน" value={<span style={{ fontFamily:"var(--font-mono)", fontWeight:600 }}>{data.employees.toLocaleString()}</span>} />}
              </Section>
            </div>

            {/* ── Analyst Consensus ── */}
            <Section title="🎯 Analyst Consensus">
              <AnalystChart
                summary={data.analyst_summary}
                recommendation={data.recommendation}
                count={data.analyst_count}
                target={data.target_mean_price} />
              {data.target_high_price && data.target_low_price && (
                <div style={{ display:"flex", gap:20, marginTop:12, fontSize:12 }}>
                  <span style={{ color:"var(--text-muted)" }}>Range:
                    <b style={{ color:"var(--red)", fontFamily:"var(--font-mono)", marginLeft:4 }}>
                      {data.target_low_price.toLocaleString("th-TH",{minimumFractionDigits:2})}
                    </b> —
                    <b style={{ color:"var(--green)", fontFamily:"var(--font-mono)", marginLeft:4 }}>
                      {data.target_high_price.toLocaleString("th-TH",{minimumFractionDigits:2})}
                    </b>
                  </span>
                </div>
              )}
            </Section>

            {/* ── Quarterly ── */}
            {data.quarterly_financials?.length > 0 && (
              <Section title="📋 งบการเงินรายไตรมาส (ล่าสุด 4 ไตรมาส)">
                <QuarterlyChart data={data.quarterly_financials} />
                <div style={{ overflowX:"auto", marginTop:16 }}>
                  <table className="data-table" style={{ fontSize:12 }}>
                    <thead>
                      <tr>
                        <th>ไตรมาส</th>
                        <th style={{ textAlign:"right" }}>Revenue</th>
                        <th style={{ textAlign:"right" }}>Gross Profit</th>
                        <th style={{ textAlign:"right" }}>Net Income</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.quarterly_financials.map((q, i) => (
                        <tr key={i}>
                          <td style={{ fontFamily:"var(--font-mono)", color:"var(--accent)" }}>{q.period}</td>
                          <td style={{ textAlign:"right", fontFamily:"var(--font-mono)" }}>
                            {q.revenue ? (q.revenue/1e9).toFixed(2)+"B" : "—"}
                          </td>
                          <td style={{ textAlign:"right", fontFamily:"var(--font-mono)", color:"var(--green)" }}>
                            {q.gross_profit ? (q.gross_profit/1e9).toFixed(2)+"B" : "—"}
                          </td>
                          <td style={{ textAlign:"right", fontFamily:"var(--font-mono)",
                            color: (q.net_income||0) >= 0 ? "var(--green)" : "var(--red)" }}>
                            {q.net_income ? (q.net_income/1e9).toFixed(2)+"B" : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>
            )}

            <div style={{ fontSize:11, color:"var(--text-muted)", textAlign:"right" }}>
              ข้อมูล ณ วันที่: {data.fetched_at} · แหล่ง: yfinance (Yahoo Finance)
            </div>
          </>
        )}

        {!loading && !data && (
          <div className="empty-state">
            <span style={{ fontSize:48 }}>📊</span>
            <span style={{ fontWeight:600 }}>ใส่รหัสหุ้นเพื่อดูข้อมูล Fundamental</span>
            <span style={{ fontSize:12, color:"var(--text-muted)" }}>P/E · EPS · งบการเงิน · Analyst Consensus</span>
          </div>
        )}
      </div>
    </div>
  )
}
