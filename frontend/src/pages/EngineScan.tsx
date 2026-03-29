/**
 * pages/EngineScan.tsx — ตัวอย่างผลสแกนที่เข้าเกณฑ์
 * แก้ไข: decision key mismatch (STRONG_BUY vs "STRONG BUY"), default score/days, symbol search autocomplete
 */
import { useState, useEffect, useRef } from "react"
import { engineApi, EngineResult } from "../api/engineApi"
import { API_BASE } from "../api/config"
import ScoreCard from "../components/ScoreCard"
import DecisionBadge from "../components/DecisionBadge"

const BASE = API_BASE.replace("/api", "")

// normalize decision key: "STRONG_BUY" → "STRONG BUY"
const normalizeDecision = (d: string) => d.replace(/_/g, " ")

// ── Symbol Autocomplete Search ────────────────────────────────────────────────
function SymbolSearch({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [results, setResults] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const timer = useRef<any>(null)
  const wrap  = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const h = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener("mousedown", h)
    return () => document.removeEventListener("mousedown", h)
  }, [])

  useEffect(() => {
    clearTimeout(timer.current)
    if (!value.trim() || value.length < 1) { setResults([]); setOpen(false); return }
    timer.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/symbols/?search=${value}&page_size=10`)
        const d = await res.json()
        setResults(d.results || [])
        setOpen(true)
      } catch { setResults([]) }
    }, 200)
  }, [value])

  const FLAG: Record<string, string> = { SET:"🇹🇭", NASDAQ:"🇺🇸", NYSE:"🇺🇸" }

  return (
    <div ref={wrap} style={{ position:"relative", flex:1, minWidth:180 }}>
      <input className="filter-input" placeholder="🔍 ค้นหารหัสหุ้น เช่น PTT, AAPL..."
        value={value} onChange={e => onChange(e.target.value.toUpperCase())}
        onKeyDown={e => e.key === "Escape" && setOpen(false)}
        style={{ width:"100%" }} autoComplete="off" />
      {open && results.length > 0 && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, zIndex:999,
          background:"var(--bg-surface,#1a2332)", border:"1px solid var(--border)",
          borderRadius:8, maxHeight:260, overflowY:"auto", boxShadow:"0 8px 24px rgba(0,0,0,.4)" }}>
          {results.map((s: any) => (
            <div key={s.symbol} onMouseDown={() => { onChange(s.symbol); setOpen(false) }}
              style={{ padding:"8px 14px", cursor:"pointer", display:"flex", gap:10, alignItems:"center",
                borderBottom:"1px solid var(--border)", transition:"background .1s" }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-elevated)")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
              <span>{FLAG[s.exchange] || "🌐"}</span>
              <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, color:"var(--accent)", minWidth:60 }}>{s.symbol}</span>
              <span style={{ fontSize:12, color:"var(--text-muted)", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s.name}</span>
              <span style={{ fontSize:10, padding:"1px 6px", borderRadius:4, flexShrink:0,
                background: s.exchange==="SET"?"#0d4f3c":"#1a2c5e",
                color: s.exchange==="SET"?"#00e676":"#7eb3ff" }}>{s.exchange}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Analyze Panel ─────────────────────────────────────────────────────────────
function AnalyzePanel({ symbol, onClose, onOpenChart }:
  { symbol: string; onClose: () => void; onOpenChart?: (s: string) => void }) {
  const [data, setData]       = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState("")

  useEffect(() => {
    setLoading(true); setError("")
    fetch(`${BASE}/engine/analyze/${symbol}/`)
      .then(r => r.json())
      .then(d => { if (d.error) setError(d.error); else setData(d) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [symbol])

  const bd  = data?.breakdown || {}
  const dec = data ? normalizeDecision(data.decision || "") : ""

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,.65)",
      display:"flex", alignItems:"center", justifyContent:"center", zIndex:1000, padding:20 }}
      onClick={onClose}>
      <div style={{ background:"var(--bg-surface,#1a2332)", border:"1px solid var(--border)",
        borderRadius:16, padding:28, width:"100%", maxWidth:560, maxHeight:"85vh", overflowY:"auto" }}
        onClick={e => e.stopPropagation()}>

        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20 }}>
          <div style={{ display:"flex", alignItems:"center", gap:12 }}>
            <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, fontSize:22, color:"var(--accent)" }}>{symbol}</span>
            {dec && <DecisionBadge decision={dec as any} />}
          </div>
          <div style={{ display:"flex", gap:8 }}>
            {onOpenChart && <button className="btn btn-ghost" style={{ fontSize:12 }}
              onClick={() => { onOpenChart(symbol); onClose() }}>📈 กราฟ</button>}
            <button onClick={onClose} style={{ background:"transparent", border:"none",
              color:"var(--text-muted)", fontSize:20, cursor:"pointer" }}>✕</button>
          </div>
        </div>

        {loading && <div className="loading-state" style={{ padding:40 }}><div className="loading-spinner" /></div>}
        {error   && <div style={{ color:"var(--red)", fontSize:13 }}>❌ {error}</div>}

        {data && !loading && (
          <>
            {/* Score ring */}
            <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom:20,
              padding:"12px 16px", background:"var(--bg-elevated)", borderRadius:10 }}>
              <div style={{ position:"relative", width:56, height:56, flexShrink:0 }}>
                <svg width="56" height="56" viewBox="0 0 56 56">
                  <circle cx="28" cy="28" r="23" fill="none" stroke="var(--border)" strokeWidth="4"/>
                  <circle cx="28" cy="28" r="23" fill="none" strokeWidth="4" strokeLinecap="round"
                    stroke={data.score>=80?"#00c853":data.score>=60?"#00e676":data.score>=40?"#ffd600":"#ff5252"}
                    strokeDasharray={`${(data.score/100)*144.5} 144.5`} transform="rotate(-90 28 28)" />
                </svg>
                <span style={{ position:"absolute", inset:0, display:"flex", alignItems:"center",
                  justifyContent:"center", fontWeight:700, fontSize:14 }}>{data.score}</span>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:4, flexShrink:0 }}>
                <span style={{ fontSize:11, fontWeight:700, padding:"2px 8px", borderRadius:4,
                  background: data.score>=80?"#00c85322":data.score>=60?"#00e67622":data.score>=40?"#ffd60022":"#ff525222",
                  color: data.score>=80?"#00c853":data.score>=60?"#00e676":data.score>=40?"#ffd600":"#ff5252" }}>
                  {data.score>=80?"⭐ ดีมาก":data.score>=60?"✅ ดี":data.score>=40?"⚠️ พอใช้":"❌ อ่อน"}
                </span>
                <span style={{ fontSize:10, color:"var(--text-muted)" }}>Score / 100</span>
              </div>
              <div style={{ flex:1, fontSize:13, display:"flex", flexWrap:"wrap", gap:"4px 16px" }}>
                {[
                  { label:"Entry",    val:`฿${(data.entry||0).toLocaleString("th-TH",{minimumFractionDigits:2})}`, color:"var(--green)" },
                  { label:"Stop Loss",val:`฿${(data.stop_loss||0).toLocaleString("th-TH",{minimumFractionDigits:2})}`, color:"var(--red)" },
                  { label:"Risk",     val:`${data.risk_pct}%`, color:"var(--yellow)" },
                  { label:"RSI",      val: data.rsi != null ? Number(data.rsi).toFixed(1) : "—", color:"var(--text-primary)" },
                  { label:"ADX",      val: data.adx != null ? Number(data.adx).toFixed(1) : "—", color:"var(--text-primary)" },
                ].map(({ label, val, color }) => (
                  <span key={label} style={{ display:"inline-flex", gap:4 }}>
                    <span style={{ color:"var(--text-muted)" }}>{label}:</span>
                    <b style={{ fontFamily:"var(--font-mono)", color }}>{val}</b>
                  </span>
                ))}
              </div>
            </div>

            {/* Breakdown bars */}
            {Object.keys(bd).length > 0 && (
              <div style={{ marginBottom:16 }}>
                <div style={{ fontSize:12, color:"var(--text-muted)", marginBottom:8, fontWeight:600 }}>Score Breakdown</div>
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
                        <div style={{ width:`${Math.min((v/max)*100,100)}%`, height:"100%", background:color, borderRadius:3 }} />
                      </div>
                    </div>
                  )
                })}
                {bd.risk_penalty > 0 && (
                  <div style={{ fontSize:11, color:"var(--red)", marginTop:4 }}>⚠️ Risk Penalty: −{bd.risk_penalty}</div>
                )}
              </div>
            )}

            {/* Reasons */}
            {data.reasons?.length > 0 && (
              <div>
                <div style={{ fontSize:12, color:"var(--text-muted)", marginBottom:8, fontWeight:600 }}>เหตุผล</div>
                <ul style={{ listStyle:"none", padding:0, margin:0, display:"flex", flexDirection:"column", gap:6 }}>
                  {data.reasons.map((r: string, i: number) => (
                    <li key={i} style={{ display:"flex", gap:8, fontSize:13,
                      padding:"6px 10px", background:"var(--bg-elevated)", borderRadius:6 }}>
                      <span style={{ color:"var(--accent)", fontWeight:700 }}>✓</span>
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
  const [error, setError]       = useState("")
  const [exchange, setExchange] = useState("")
  const [minScore, setMinScore] = useState(0)
  const [topN, setTopN]         = useState(20)
  const [search, setSearch]     = useState("")
  const [selected, setSelected] = useState<string | null>(null)
  const [days, setDays]         = useState(30)

  // ใช้ ref เก็บ latest state เพื่อให้ load() เข้าถึงค่าล่าสุดเสมอ
  const stateRef = useRef({ exchange, minScore, topN, days })
  useEffect(() => { stateRef.current = { exchange, minScore, topN, days } }, [exchange, minScore, topN, days])

  async function load() {
    const { exchange: ex, minScore: ms, topN: tn, days: d } = stateRef.current
    setLoading(true); setError("")
    try {
      const params = new URLSearchParams()
      if (ex)  params.set("exchange",  ex)
      params.set("top",       String(tn))
      params.set("min_score", String(ms))
      params.set("days",      String(d))
      const res = await fetch(`${BASE}/engine/scan/?${params}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data.results || [])
      if ((data.results || []).length === 0) setError("ไม่พบสัญญาณในช่วงเวลาที่เลือก")
    } catch (e: any) {
      setError(e.message || "เกิดข้อผิดพลาด")
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])  // โหลดครั้งแรก

  const filtered = results
    .map(r => ({ ...r, decision: normalizeDecision(r.decision || "") as any }))
    .filter(r => !search || r.symbol.includes(search.toUpperCase()))

  const DECISION_ORDER = ["STRONG BUY","BUY","HOLD","WATCH","SELL"]
  const DECISION_COLORS: Record<string,string> = {
    "STRONG BUY":"#00c853","BUY":"#00e676","HOLD":"#ffd600","WATCH":"#29b6f6","SELL":"#ff5252"
  }
  const DECISION_LABELS: Record<string,string> = {
    "STRONG BUY":"โมเมนตัมบวกแรง","BUY":"โมเมนตัมบวก",
    "HOLD":"รอสัญญาณชัด","WATCH":"เฝ้าดู","SELL":"โมเมนตัมลบ"
  }

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">🔥 ตัวอย่างผลสแกนที่เข้าเกณฑ์</div>
        <div className="page-subtitle">5-Factor Scoring Engine · คลิกหุ้นเพื่อดู Full Analysis</div>
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
                {([
                  { val:0,  label:"All",  hint:"ทั้งหมด" },
                  { val:40, label:"≥40",  hint:"พอใช้" },
                  { val:60, label:"≥60",  hint:"ดี" },
                  { val:80, label:"≥80",  hint:"ดีมาก" },
                ] as const).map(({ val, label, hint }) => (
                  <button key={val} onClick={() => setMinScore(val)}
                    title={`Score ${label} — ${hint}`}
                    style={{
                      padding:"6px 12px", borderRadius:6, fontSize:12, fontWeight:600, cursor:"pointer",
                      border:`1px solid ${minScore===val?"var(--accent)":"var(--border)"}`,
                      background: minScore===val?"var(--accent-dim)":"transparent",
                      color: minScore===val?"var(--accent)":"var(--text-muted)",
                      display:"flex", flexDirection:"column", alignItems:"center", gap:1,
                    }}>
                    <span>{label}</span>
                    <span style={{ fontSize:9, fontWeight:400, opacity:0.7 }}>{hint}</span>
                  </button>
                ))}
              </div>
              <div style={{ fontSize:10, color:"var(--text-muted)", marginTop:5 }}>
                ≥80 ดีมาก · ≥60 ดี · ≥40 พอใช้ · &lt;40 อ่อน (0–100)
              </div>
            </div>

            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>Top</div>
              <select className="filter-select" value={topN} onChange={e => setTopN(Number(e.target.value))}>
                {[10,20,50,100].map(n => <option key={n} value={n}>Top {n}</option>)}
              </select>
            </div>

            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>ช่วงเวลา</div>
              <select className="filter-select" value={days} onChange={e => setDays(Number(e.target.value))}>
                {[7,14,30,60,90].map(d => <option key={d} value={d}>{d} วัน</option>)}
              </select>
            </div>

            {/* Symbol search with autocomplete */}
            <div style={{ flex:1, minWidth:200 }}>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>
                ค้นหารหัสหุ้น
                <span style={{ marginLeft:6, fontSize:10, color:"var(--text-muted)", fontWeight:400 }}>
                  (พิมพ์เพื่อ filter · กด Scan เพื่อค้นหาข้อมูลใหม่)
                </span>
              </div>
              <SymbolSearch value={search} onChange={setSearch} />
            </div>

            <button className="btn btn-primary" onClick={load} disabled={loading}
              style={{ height:38, minWidth:100, flexShrink:0 }}>
              {loading ? "⏳..." : "🔍 Scan"}
            </button>
          </div>
        </div>

        {/* Summary badges */}
        {filtered.length > 0 && (
          <div style={{ display:"flex", gap:10, marginBottom:20, flexWrap:"wrap", alignItems:"center" }}>
            {DECISION_ORDER.map(label => {
              const count = filtered.filter(r => r.decision === label).length
              const color = DECISION_COLORS[label]
              return count > 0 ? (
                <div key={label} style={{ background:`${color}15`, border:`1px solid ${color}44`,
                  borderRadius:8, padding:"5px 14px", fontSize:12, fontWeight:700, color }}>
                  {DECISION_LABELS[label] ?? label} {count}
                </div>
              ) : null
            })}
            <span style={{ marginLeft:"auto", fontSize:12, color:"var(--text-muted)" }}>
              แสดง {filtered.length} จาก {results.length} หุ้น ({days} วัน)
            </span>
          </div>
        )}

        {/* Grid */}
        {loading ? (
          <div className="loading-state"><div className="loading-spinner" /><span>กำลัง scan...</span></div>
        ) : error && filtered.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize:48 }}>🔍</span>
            <span>{error}</span>
            <button className="btn btn-primary"
              onClick={() => {
                setMinScore(0); setDays(90)
                stateRef.current = { ...stateRef.current, minScore:0, days:90 }
                load()
              }}
              style={{ marginTop:12 }}>ดูทั้งหมด (90 วัน)</button>
          </div>
        ) : (
          <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))", gap:16 }}>
            {filtered.map(r => (
              <ScoreCard key={r.symbol} data={r} onClick={() => setSelected(r.symbol)} />
            ))}
          </div>
        )}
      </div>

      {selected && (
        <AnalyzePanel symbol={selected} onClose={() => setSelected(null)} onOpenChart={onOpenChart} />
      )}
    </div>
  )
}
