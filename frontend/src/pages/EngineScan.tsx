/**
 * pages/EngineScan.tsx
 * Top Opportunities — 5-Factor Scoring Engine
 * คลิกหุ้นเพื่อดู full analysis panel (entry, stop loss, reasons)
 */
import { useState, useEffect } from "react"
import { engineApi, EngineResult } from "../api/engineApi"
import ScoreCard from "../components/ScoreCard"
import DecisionBadge from "../components/DecisionBadge"

const BASE = (import.meta as any).env.VITE_API_URL?.replace("/api","") || "http://127.0.0.1:8000"

// ── Analyze Panel ─────────────────────────────────────────────────────────────
function AnalyzePanel({ symbol, onClose, onOpenChart }:
  { symbol: string; onClose: () => void; onOpenChart?: (s: string) => void }) {
  const [data, setData]     = useState<EngineResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState("")

  useEffect(() => {
    setLoading(true); setError("")
    fetch(`${BASE}/engine/analyze/${symbol}/`)
      .then(r => r.json())
      .then(d => { if (d.error) setError(d.error); else setData(d) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [symbol])

  const bd = (data as any)?.breakdown || {}

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.65)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: 20,
    }} onClick={onClose}>
      <div style={{
        background: "var(--bg-surface,#1a2332)", border: "1px solid var(--border)",
        borderRadius: 16, padding: 28, width: "100%", maxWidth: 560,
        maxHeight: "85vh", overflowY: "auto",
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, fontSize:22, color:"var(--accent)" }}>
              {symbol}
            </span>
            {data && <DecisionBadge decision={data.decision} />}
          </div>
          <div style={{ display:"flex", gap:8 }}>
            {onOpenChart && (
              <button className="btn btn-ghost" style={{ fontSize:12 }}
                onClick={() => { onOpenChart(symbol); onClose() }}>📈 กราฟ</button>
            )}
            <button onClick={onClose} style={{ background:"transparent", border:"none",
              color:"var(--text-muted)", fontSize:20, cursor:"pointer" }}>✕</button>
          </div>
        </div>

        {loading && <div className="loading-state" style={{ padding:40 }}><div className="loading-spinner" /></div>}
        {error   && <div style={{ color:"var(--red)", fontSize:13 }}>❌ {error}</div>}

        {data && (
          <>
            {/* Score */}
            <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:20,
              padding:"12px 16px", background:"var(--bg-elevated)", borderRadius:10 }}>
              <div style={{ position:"relative", width:56, height:56, flexShrink:0 }}>
                <svg width="56" height="56" viewBox="0 0 56 56">
                  <circle cx="28" cy="28" r="23" fill="none" stroke="var(--border)" strokeWidth="4"/>
                  <circle cx="28" cy="28" r="23" fill="none"
                    stroke={data.score >= 80?"#00c853": data.score >= 60?"#00e676": data.score >= 40?"#ffd600":"#ff5252"}
                    strokeWidth="4" strokeLinecap="round"
                    strokeDasharray={`${(data.score/100)*144.5} 144.5`}
                    transform="rotate(-90 28 28)" />
                </svg>
                <span style={{ position:"absolute", inset:0, display:"flex", alignItems:"center",
                  justifyContent:"center", fontWeight:700, fontSize:14 }}>{data.score}</span>
              </div>
              <div style={{ flex:1, fontSize:13 }}>
                {[
                  { label:"Entry",     val: `฿${data.entry?.toLocaleString("th-TH",{minimumFractionDigits:2})}`, color:"var(--green)"  },
                  { label:"Stop Loss", val: `฿${data.stop_loss?.toLocaleString("th-TH",{minimumFractionDigits:2})}`, color:"var(--red)" },
                  { label:"Risk",      val: `${data.risk_pct}%`, color:"var(--yellow)" },
                  { label:"RSI",       val: data.rsi?.toFixed(1) ?? "—", color:"var(--text-primary)" },
                  { label:"ADX",       val: data.adx?.toFixed(1) ?? "—", color:"var(--text-primary)" },
                ].map(({ label, val, color }) => (
                  <span key={label} style={{ marginRight:16, display:"inline-flex", gap:4 }}>
                    <span style={{ color:"var(--text-muted)" }}>{label}:</span>
                    <b style={{ fontFamily:"var(--font-mono)", color }}>{val}</b>
                  </span>
                ))}
              </div>
            </div>

            {/* Score Breakdown */}
            {Object.keys(bd).length > 0 && (
              <div style={{ marginBottom:16 }}>
                <div style={{ fontSize:12, color:"var(--text-muted)", marginBottom:8, fontWeight:600 }}>
                  Score Breakdown
                </div>
                {[
                  { key:"trend",      label:"Trend",      max:40, color:"#00d4ff" },
                  { key:"momentum",   label:"Momentum",   max:25, color:"#ffd740" },
                  { key:"volume",     label:"Volume",     max:15, color:"#69f0ae" },
                  { key:"volatility", label:"Volatility", max:10, color:"#ce93d8" },
                ].map(({ key, label, max, color }) => {
                  const v = bd[key] ?? 0
                  return (
                    <div key={key} style={{ marginBottom:6 }}>
                      <div style={{ display:"flex", justifyContent:"space-between", fontSize:11, marginBottom:2 }}>
                        <span style={{ color:"var(--text-muted)" }}>{label}</span>
                        <span style={{ fontFamily:"var(--font-mono)", color }}>{v}/{max}</span>
                      </div>
                      <div style={{ height:5, background:"var(--border)", borderRadius:3 }}>
                        <div style={{ width:`${(v/max)*100}%`, height:"100%", background:color, borderRadius:3 }} />
                      </div>
                    </div>
                  )
                })}
                {bd.risk_penalty > 0 && (
                  <div style={{ fontSize:11, color:"var(--red)", marginTop:4 }}>
                    ⚠️ Risk Penalty: −{bd.risk_penalty}
                  </div>
                )}
              </div>
            )}

            {/* Reasons */}
            {data.reasons?.length > 0 && (
              <div>
                <div style={{ fontSize:12, color:"var(--text-muted)", marginBottom:8, fontWeight:600 }}>
                  เหตุผล
                </div>
                <ul style={{ listStyle:"none", padding:0, margin:0, display:"flex", flexDirection:"column", gap:6 }}>
                  {data.reasons.map((r, i) => (
                    <li key={i} style={{ display:"flex", gap:8, fontSize:13,
                      padding:"6px 10px", background:"var(--bg-elevated)", borderRadius:6 }}>
                      <span style={{ color:"var(--accent)", fontWeight:700, flexShrink:0 }}>✓</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function EngineScan({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [results, setResults]   = useState<EngineResult[]>([])
  const [loading, setLoading]   = useState(false)
  const [exchange, setExchange] = useState("")
  const [minScore, setMinScore] = useState(60)
  const [topN, setTopN]         = useState(20)
  const [search, setSearch]     = useState("")
  const [selected, setSelected] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try {
      const res = await engineApi.scan({ exchange: exchange || undefined, top: topN, min_score: minScore })
      setResults(res.results || [])
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const filtered = results.filter(r =>
    !search || r.symbol.includes(search.toUpperCase())
  )

  const DECISION_ORDER = ["STRONG BUY","BUY","HOLD","WATCH","SELL"]
  const DECISION_COLORS: Record<string,string> = {
    "STRONG BUY":"#00c853", "BUY":"#00e676", "HOLD":"#ffd600", "WATCH":"#29b6f6", "SELL":"#ff5252"
  }

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">🔥 Top Opportunities</div>
        <div className="page-subtitle">Scan ทุกหุ้นด้วย 5-Factor Scoring Engine · คลิกหุ้นเพื่อดู Analysis</div>
      </div>
      <div className="page-body">

        {/* Controls */}
        <div className="card" style={{ marginBottom:20 }}>
          <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"flex-end" }}>
            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>ตลาด</div>
              <select className="filter-select" value={exchange} onChange={e => setExchange(e.target.value)}>
                <option value="">ทุกตลาด</option>
                <option value="SET">🇹🇭 SET</option>
                <option value="NYSE">🇺🇸 NYSE</option>
                <option value="NASDAQ">🇺🇸 NASDAQ</option>
              </select>
            </div>

            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>Score ขั้นต่ำ</div>
              <div style={{ display:"flex", gap:4 }}>
                {[0,40,60,80].map(s => (
                  <button key={s} onClick={() => setMinScore(s)} style={{
                    padding:"6px 12px", borderRadius:6, fontSize:12, fontWeight:600, cursor:"pointer",
                    border:`1px solid ${minScore===s?"var(--accent)":"var(--border)"}`,
                    background: minScore===s?"var(--accent-dim)":"transparent",
                    color: minScore===s?"var(--accent)":"var(--text-muted)",
                  }}>{s===0?"All":`≥${s}`}</button>
                ))}
              </div>
            </div>

            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>Top</div>
              <select className="filter-select" value={topN} onChange={e => setTopN(Number(e.target.value))}>
                {[10,20,50].map(n => <option key={n} value={n}>Top {n}</option>)}
              </select>
            </div>

            <input className="filter-input" placeholder="🔍 ค้นหารหัสหุ้น..."
              value={search} onChange={e => setSearch(e.target.value)} style={{ minWidth:160 }} />

            <button className="btn btn-primary" onClick={load} disabled={loading} style={{ height:38, minWidth:100 }}>
              {loading ? "⏳..." : "🔍 Scan"}
            </button>
          </div>
        </div>

        {/* Summary badges */}
        {results.length > 0 && (
          <div style={{ display:"flex", gap:10, marginBottom:20, flexWrap:"wrap", alignItems:"center" }}>
            {DECISION_ORDER.map(label => {
              const count = filtered.filter(r => r.decision === label).length
              const color = DECISION_COLORS[label]
              return count > 0 ? (
                <div key={label} style={{ background:`${color}15`, border:`1px solid ${color}44`,
                  borderRadius:8, padding:"5px 14px", fontSize:12, fontWeight:700, color }}>
                  {label} {count}
                </div>
              ) : null
            })}
            <span style={{ marginLeft:"auto", fontSize:12, color:"var(--text-muted)" }}>
              {filtered.length} จาก {results.length} หุ้น
            </span>
          </div>
        )}

        {/* Grid */}
        {loading ? (
          <div className="loading-state"><div className="loading-spinner" /><span>กำลัง scan...</span></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize:48 }}>🔍</span>
            <span>ไม่พบหุ้นที่ตรงเงื่อนไข — ลองปรับ Score ขั้นต่ำ</span>
          </div>
        ) : (
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill, minmax(260px,1fr))", gap:16 }}>
            {filtered.map(r => (
              <ScoreCard key={r.symbol} data={r} onClick={() => setSelected(r.symbol)} />
            ))}
          </div>
        )}
      </div>

      {/* Analyze Modal */}
      {selected && (
        <AnalyzePanel symbol={selected} onClose={() => setSelected(null)} onOpenChart={onOpenChart} />
      )}
    </div>
  )
}
