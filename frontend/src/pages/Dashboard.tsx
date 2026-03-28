import { useState, useEffect, useCallback } from "react"
import { api } from "../api/client"
import { SignalInfo } from "../api/types"
import { TermText } from "../components/TermAssistant"

const SIGNAL_LABELS: Record<string, string> = {
  BUY:"ซื้อ", STRONG_BUY:"ซื้อแรง", BREAKOUT:"Breakout",
  GOLDEN_CROSS:"Golden✕", OVERSOLD:"Oversold", EMA_ALIGNMENT:"EMA Align",
  EMA_PULLBACK:"EMA Pull", SELL:"ขาย", STRONG_SELL:"ขายแรง",
  DEATH_CROSS:"Death✕", BREAKDOWN:"Breakdown", OVERBOUGHT:"Overbought",
  WATCH:"เฝ้าดู", ALERT:"แจ้งเตือน",
}
const SIGNAL_EMOJIS: Record<string, string> = {
  BUY:"🟢", STRONG_BUY:"💚", BREAKOUT:"🚀", GOLDEN_CROSS:"⭐", OVERSOLD:"🔵",
  SELL:"🔴", STRONG_SELL:"❤️", DEATH_CROSS:"💀", BREAKDOWN:"💥", OVERBOUGHT:"🟡",
  WATCH:"👁️", ALERT:"⚠️", EMA_ALIGNMENT:"📈", EMA_PULLBACK:"↩️",
}
const SIG_COLOR: Record<string,string> = {
  BUY:"var(--green)", STRONG_BUY:"#00c853", GOLDEN_CROSS:"#00c853",
  EMA_ALIGNMENT:"var(--green)", EMA_PULLBACK:"var(--green)", OVERSOLD:"var(--blue)",
  BREAKOUT:"var(--accent)", SELL:"var(--red)", STRONG_SELL:"#d50000",
  DEATH_CROSS:"var(--red)", BREAKDOWN:"var(--red)", OVERBOUGHT:"var(--yellow)",
  WATCH:"var(--text-muted)", ALERT:"var(--yellow)",
}

function formatTime(iso: string) {
  if (!iso) return "-"
  return new Date(iso).toLocaleString("th-TH", {
    month:"short", day:"numeric", hour:"2-digit", minute:"2-digit"
  })
}

function Badge({ type }: { type: string }) {
  const color = SIG_COLOR[type] || "var(--text-muted)"
  const label = SIGNAL_LABELS[type] || type
  const emoji = SIGNAL_EMOJIS[type] || ""
  return (
    <span style={{
      fontSize:11, fontWeight:700, padding:"2px 8px", borderRadius:4,
      background:`${color}18`, color, border:`1px solid ${color}44`,
      whiteSpace:"nowrap", display:"inline-flex", alignItems:"center", gap:4,
    }}>{emoji} {label}</span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const s = Number(score) || 0
  const color = s>=80?"#00c853":s>=60?"var(--green)":s>=40?"var(--yellow)":"var(--red)"
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
      <div style={{ flex:1, height:5, background:"var(--border)", borderRadius:3 }}>
        <div style={{ width:`${s}%`, height:"100%", background:color, borderRadius:3 }} />
      </div>
      <span style={{ fontFamily:"var(--font-mono)", fontSize:12, fontWeight:700, color, minWidth:28, textAlign:"right" }}>
        {s>0?s.toFixed(0):"-"}
      </span>
    </div>
  )
}

// ── Signal Table ─────────────────────────────────────────
function SignalTable({ signals, onOpenChart }: { signals: SignalInfo[], onOpenChart:(s:string)=>void }) {
  if (signals.length === 0)
    return <div style={{ textAlign:"center", padding:"40px 0", color:"var(--text-muted)", fontSize:13 }}>ไม่พบสัญญาณที่ตรงเงื่อนไข</div>

  return (
    <div style={{ overflowX:"auto" }}>
      <table className="data-table" style={{ fontSize:13 }}>
        <thead>
          <tr>
            <th style={{ paddingLeft:16 }}>หุ้น</th>
            <th>สัญญาณ</th>
            <th style={{ textAlign:"right" }}>ราคา</th>
            <th style={{ textAlign:"right" }}>Stop Loss</th>
            <th style={{ textAlign:"right" }}>Risk %</th>
            <th style={{ minWidth:130 }}>Score</th>
            <th style={{ textAlign:"right", paddingRight:16 }}>เวลา</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => (
            <tr key={i} onClick={() => onOpenChart(s.symbol_code)} style={{ cursor:"pointer" }}>
              <td style={{ paddingLeft:16 }}>
                <div style={{ display:"flex", flexDirection:"column" }}>
                  <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, fontSize:14, color:"var(--accent)" }}>
                    {s.symbol_code}
                  </span>
                  <span style={{ fontSize:11, color:"var(--text-muted)" }}>{s.symbol_name}</span>
                </div>
              </td>
              <td><Badge type={s.signal_type} /></td>
              <td style={{ textAlign:"right", fontFamily:"var(--font-mono)", fontWeight:600 }}>
                {s.price?.toLocaleString("th-TH",{minimumFractionDigits:2})||"-"}
              </td>
              <td style={{ textAlign:"right", fontFamily:"var(--font-mono)", color:"var(--red)", fontSize:12 }}>
                {(s as any).stop_loss?.toLocaleString("th-TH",{minimumFractionDigits:2})||"-"}
              </td>
              <td style={{ textAlign:"right", fontFamily:"var(--font-mono)", fontSize:12, color:"var(--yellow)" }}>
                {(s as any).risk_pct?`${(s as any).risk_pct}%`:"-"}
              </td>
              <td style={{ minWidth:130 }}><ScoreBar score={s.score} /></td>
              <td style={{ textAlign:"right", fontSize:11, color:"var(--text-muted)", paddingRight:16, whiteSpace:"nowrap" }}>
                {formatTime(s.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Filter Bar ────────────────────────────────────────────
interface FilterState {
  signal_type: string; exchange: string; days: string
  direction: string; min_score: string
}
const DEFAULT_FILTER: FilterState = {
  signal_type:"", exchange:"", days:"7", direction:"", min_score:""
}

// ── Tab Config ────────────────────────────────────────────
const TABS = [
  { id:"all",      label:"ทั้งหมด",      icon:"📋", dir:"",      color:"var(--text-primary)" },
  { id:"buy",      label:"สัญญาณซื้อ",   icon:"🟢", dir:"LONG",  color:"var(--green)" },
  { id:"sell",     label:"สัญญาณขาย",   icon:"🔴", dir:"SHORT", color:"var(--red)"   },
  { id:"breakout", label:"Breakout",    icon:"🚀", dir:"",      color:"var(--accent)" },
  { id:"watch",    label:"เฝ้าดู",      icon:"👁️", dir:"",      color:"var(--text-muted)" },
]

// ── Main Dashboard ────────────────────────────────────────
export default function Dashboard({ onOpenChart }: { onOpenChart:(s:string)=>void, ws:any }) {
  const [stats, setStats]       = useState<any>({})
  const [signals, setSignals]   = useState<SignalInfo[]>([])
  const [loading, setLoading]   = useState(true)
  const [sigLoading, setSigLoading] = useState(false)
  const [activeTab, setActiveTab]   = useState("all")
  const [filter, setFilter]         = useState<FilterState>(DEFAULT_FILTER)
  const BASE = (import.meta as any).env.VITE_API_URL || "http://127.0.0.1:8000/api"

  // โหลด stats ครั้งแรก
  useEffect(() => {
    api.getDashboard()
      .then(d => setStats(d?.stats || {}))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // โหลด signals ตาม filter + tab
  const loadSignals = useCallback(() => {
    setSigLoading(true)
    const tab = TABS.find(t => t.id === activeTab)!
    const params: Record<string,string> = { days: filter.days, page_size:"100" }
    if (filter.exchange)    params.exchange    = filter.exchange
    if (filter.min_score)   params.min_score   = filter.min_score
    // direction จาก tab หรือ manual filter
    const dir = tab.dir || filter.direction
    if (dir) params.direction = dir
    // signal_type จาก filter หรือ tab preset
    if (filter.signal_type) {
      params.signal_type = filter.signal_type
    } else if (activeTab === "breakout") {
      params.signal_type = "BREAKOUT"
    } else if (activeTab === "watch") {
      params.signal_type = "WATCH"
    }

    api.getSignals(params)
      .then(d => setSignals(d.results || []))
      .catch(console.error)
      .finally(() => setSigLoading(false))
  }, [activeTab, filter])

  useEffect(() => { loadSignals() }, [loadSignals])

  function setF(k: keyof FilterState, v: string) {
    setFilter(f => ({ ...f, [k]: v }))
  }

  // summary counts
  const bullish = signals.filter(s => ["BUY","STRONG_BUY","BREAKOUT","GOLDEN_CROSS","OVERSOLD","EMA_ALIGNMENT","EMA_PULLBACK"].includes(s.signal_type)).length
  const bearish = signals.filter(s => ["SELL","STRONG_SELL","DEATH_CROSS","BREAKDOWN","OVERBOUGHT"].includes(s.signal_type)).length
  const avgScore = signals.length > 0
    ? (signals.reduce((a,r) => a + (Number(r.score)||0), 0) / signals.length).toFixed(0)
    : "—"

  if (loading) return <div className="loading-state"><div className="loading-spinner"/><span>กำลังโหลด...</span></div>

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📡 Radar หุ้น</div>
        <div className="page-subtitle">ภาพรวมตลาด · สัญญาณซื้อขาย · กรองและค้นหาได้ทันที</div>
      </div>
      <div className="page-body">

        {/* ── Stats Row ── */}
        <div className="stats-grid" style={{ marginBottom:16 }}>
          {[
            { label:"หุ้นทั้งหมด",  val:stats.total_symbols, color:"accent" },
            { label:"Bullish",      val:bullish,              color:"green"  },
            { label:"Bearish",      val:bearish,              color:"red"    },
            { label:"สัญญาณรวม",   val:signals.length,       color:"yellow" },
            { label:"Score เฉลี่ย", val:avgScore,             color:"accent" },
          ].map(({ label, val, color }) => (
            <div key={label} className={`stat-card ${color}`}>
              <div className="stat-label">{label}</div>
              <div className="stat-value">{(val||0).toLocaleString?.() ?? val}</div>
            </div>
          ))}
        </div>

        {/* ── Main Layout ── */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 240px", gap:16 }}>

          {/* ── Left: Signal Panel ── */}
          <div>
            {/* Tab Bar */}
            <div style={{ display:"flex", borderBottom:"1px solid var(--border)", marginBottom:0,
              background:"var(--bg-surface)", borderRadius:"12px 12px 0 0",
              border:"1px solid var(--border)", borderBottomColor:"transparent", padding:"0 8px" }}>
              {TABS.map(tab => (
                <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                  padding:"10px 14px", fontSize:12, fontWeight:700, cursor:"pointer",
                  border:"none", background:"transparent",
                  borderBottom: activeTab===tab.id?`2px solid ${tab.color}`:"2px solid transparent",
                  color: activeTab===tab.id?tab.color:"var(--text-muted)",
                  display:"flex", alignItems:"center", gap:5, transition:"color 0.15s",
                  marginBottom:-1, whiteSpace:"nowrap",
                }}>
                  {tab.icon} {tab.label}
                </button>
              ))}
            </div>

            {/* Filter Bar */}
            <div style={{ background:"var(--bg-elevated)", border:"1px solid var(--border)",
              borderTop:"none", padding:"10px 14px", display:"flex", gap:8, flexWrap:"wrap", alignItems:"center" }}>
              <select className="filter-select" style={{ fontSize:11 }} value={filter.signal_type}
                onChange={e => setF("signal_type", e.target.value)}>
                <option value="">ทุกสัญญาณ</option>
                {Object.entries(SIGNAL_LABELS).map(([k,v]) => (
                  <option key={k} value={k}>{SIGNAL_EMOJIS[k]} {v}</option>
                ))}
              </select>
              <select className="filter-select" style={{ fontSize:11 }} value={filter.exchange}
                onChange={e => setF("exchange", e.target.value)}>
                <option value="">ทุกตลาด</option>
                <option value="SET">🇹🇭 SET</option>
                <option value="NASDAQ">🇺🇸 NASDAQ</option>
                <option value="NYSE">🇺🇸 NYSE</option>
              </select>
              <select className="filter-select" style={{ fontSize:11 }} value={filter.days}
                onChange={e => setF("days", e.target.value)}>
                <option value="1">วันนี้</option>
                <option value="7">7 วัน</option>
                <option value="30">30 วัน</option>
                <option value="90">90 วัน</option>
              </select>
              <input className="filter-select" style={{ width:80, fontSize:11 }}
                placeholder="Score ≥" type="number"
                value={filter.min_score} onChange={e => setF("min_score", e.target.value)} />
              <button className="btn btn-primary" style={{ fontSize:11, padding:"5px 14px", height:30 }}
                onClick={loadSignals}>กรอง</button>
              {(filter.signal_type||filter.exchange||filter.min_score||filter.days!=="7") && (
                <button className="btn btn-ghost" style={{ fontSize:11, padding:"5px 10px", height:30 }}
                  onClick={() => setFilter(DEFAULT_FILTER)}>✕ ล้าง</button>
              )}
              <span style={{ marginLeft:"auto", fontSize:11, color:"var(--text-muted)" }}>
                {sigLoading ? "⏳" : `${signals.length} รายการ`}
              </span>
            </div>

            {/* Signal Table */}
            <div style={{ background:"var(--bg-surface)", border:"1px solid var(--border)",
              borderTop:"none", borderRadius:"0 0 12px 12px", overflow:"hidden" }}>
              {sigLoading
                ? <div className="loading-state" style={{ height:300 }}><div className="loading-spinner"/><span>กำลังโหลด...</span></div>
                : <SignalTable signals={signals} onOpenChart={onOpenChart} />
              }
            </div>
          </div>

          {/* ── Right: Sidebar ── */}
          <div style={{ display:"flex", flexDirection:"column", gap:16 }}>

            {/* Market breakdown */}
            <div className="card">
              <div className="card-title">🌏 สัญญาณตามตลาด</div>
              {["SET","NASDAQ","NYSE"].map(ex => {
                const cnt = signals.filter(s => s.exchange===ex).length
                if (!cnt) return null
                return (
                  <div key={ex} style={{ marginBottom:10 }}>
                    <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3, fontSize:12 }}>
                      <span style={{ fontWeight:600 }}>{ex}</span>
                      <span style={{ fontFamily:"var(--font-mono)", color:"var(--accent)" }}>{cnt}</span>
                    </div>
                    <div style={{ background:"var(--border)", borderRadius:2, height:4 }}>
                      <div style={{ background:"var(--accent)", borderRadius:2, height:"100%",
                        width:`${(cnt/Math.max(signals.length,1))*100}%` }} />
                    </div>
                  </div>
                )
              })}
              {signals.length === 0 && <div style={{ fontSize:12, color:"var(--text-muted)" }}>ไม่มีข้อมูล</div>}
            </div>


          </div>
        </div>

      </div>
    </div>
  )
}
