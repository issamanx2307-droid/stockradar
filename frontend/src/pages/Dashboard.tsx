import { useState, useEffect } from "react"
import { api } from "../api/client"
import { SignalInfo, DashboardResponse } from "../api/types"
import { TermText } from "../components/TermAssistant"

const SIGNAL_LABELS: Record<string, string> = {
  BUY:"ซื้อ", STRONG_BUY:"ซื้อแรง", BREAKOUT:"Breakout",
  GOLDEN_CROSS:"Golden✕", OVERSOLD:"Oversold", EMA_ALIGNMENT:"EMA Align",
  EMA_PULLBACK:"EMA Pull", SELL:"ขาย", STRONG_SELL:"ขายแรง",
  DEATH_CROSS:"Death✕", BREAKDOWN:"Breakdown", OVERBOUGHT:"Overbought",
  WATCH:"เฝ้าดู", ALERT:"แจ้งเตือน",
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
  return new Date(iso).toLocaleString("th-TH", { month:"short", day:"numeric", hour:"2-digit", minute:"2-digit" })
}

function Badge({ type }: { type: string }) {
  const color = SIG_COLOR[type] || "var(--text-muted)"
  const label = SIGNAL_LABELS[type] || type
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
      background: `${color}18`, color, border: `1px solid ${color}44`,
      whiteSpace: "nowrap",
    }}>{label}</span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const s = Number(score) || 0
  const color = s >= 80 ? "#00c853" : s >= 60 ? "var(--green)" : s >= 40 ? "var(--yellow)" : "var(--red)"
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6 }}>
      <div style={{ flex:1, height:5, background:"var(--border)", borderRadius:3 }}>
        <div style={{ width:`${s}%`, height:"100%", background:color, borderRadius:3 }} />
      </div>
      <span style={{ fontFamily:"var(--font-mono)", fontSize:12, fontWeight:700, color, minWidth:28, textAlign:"right" }}>
        {s > 0 ? s.toFixed(0) : "-"}
      </span>
    </div>
  )
}

// ── Signal Table Component ────────────────────────────────
function SignalTable({ signals, onOpenChart }: { signals: SignalInfo[], onOpenChart: (s:string)=>void }) {
  if (signals.length === 0)
    return <div style={{ textAlign:"center", padding:"32px 0", color:"var(--text-muted)", fontSize:13 }}>ไม่มีสัญญาณในช่วง 7 วัน</div>

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
            <th style={{ minWidth:140 }}>Score</th>
            <th style={{ textAlign:"right", paddingRight:16 }}>เวลา</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((s, i) => (
            <tr key={i} onClick={() => onOpenChart(s.symbol_code)}
              style={{ cursor:"pointer" }}>
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
                {s.price?.toLocaleString("th-TH", { minimumFractionDigits:2 }) || "-"}
              </td>
              <td style={{ textAlign:"right", fontFamily:"var(--font-mono)", color:"var(--red)", fontSize:12 }}>
                {(s as any).stop_loss?.toLocaleString("th-TH", { minimumFractionDigits:2 }) || "-"}
              </td>
              <td style={{ textAlign:"right", fontFamily:"var(--font-mono)", fontSize:12, color:"var(--yellow)" }}>
                {(s as any).risk_pct ? `${(s as any).risk_pct}%` : "-"}
              </td>
              <td style={{ minWidth:140 }}><ScoreBar score={s.score} /></td>
              <td style={{ textAlign:"right", fontSize:11, color:"var(--text-muted)", paddingRight:16 }}>
                {formatTime(s.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Tabbed Signal Section ─────────────────────────────────
const TABS = [
  { id:"buy",      label:"สัญญาณซื้อ",  icon:"🟢", color:"var(--green)" },
  { id:"sell",     label:"สัญญาณขาย",  icon:"🔴", color:"var(--red)"   },
  { id:"breakout", label:"Breakout",   icon:"🚀", color:"var(--accent)" },
  { id:"watch",    label:"เฝ้าดู",     icon:"👁️", color:"var(--text-muted)" },
]

function SignalTabs({ buyList, sellList, breakoutList, watchList, stats, onOpenChart }: {
  buyList: SignalInfo[], sellList: SignalInfo[],
  breakoutList: SignalInfo[], watchList: SignalInfo[],
  stats: any, onOpenChart: (s:string)=>void
}) {
  const [active, setActive] = useState("buy")

  const tabData: Record<string,SignalInfo[]> = {
    buy: buyList, sell: sellList, breakout: breakoutList, watch: watchList,
  }
  const tabCount: Record<string,number> = {
    buy:      stats?.buy_signals    || buyList.length,
    sell:     stats?.sell_signals   || sellList.length,
    breakout: stats?.breakout_count || breakoutList.length,
    watch:    stats?.watch_count    || watchList.length,
  }

  return (
    <div className="card" style={{ padding:0 }}>
      {/* Tab Headers */}
      <div style={{ display:"flex", borderBottom:"1px solid var(--border)", padding:"0 8px" }}>
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => setActive(tab.id)} style={{
            padding:"12px 16px", fontSize:13, fontWeight:700, cursor:"pointer",
            border:"none", background:"transparent",
            borderBottom: active===tab.id ? `2px solid ${tab.color}` : "2px solid transparent",
            color: active===tab.id ? tab.color : "var(--text-muted)",
            display:"flex", alignItems:"center", gap:6, transition:"color 0.15s",
            marginBottom:-1,
          }}>
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            <span style={{
              fontSize:10, fontWeight:700, padding:"1px 6px", borderRadius:10,
              background: active===tab.id ? `${tab.color}20` : "var(--bg-elevated)",
              color: active===tab.id ? tab.color : "var(--text-muted)",
            }}>{tabCount[tab.id]}</span>
          </button>
        ))}
      </div>
      {/* Tab Content */}
      <div style={{ padding:"4px 0 8px" }}>
        <SignalTable signals={tabData[active]} onOpenChart={onOpenChart} />
      </div>
    </div>
  )
}

// ── Quick Actions ─────────────────────────────────────────
function QuickActions() {
  const [scanning, setScanning] = useState(false)
  const [done, setDone]         = useState(false)
  const [count, setCount]       = useState(0)

  async function handleScan() {
    setScanning(true); setDone(false)
    try {
      const res = await fetch("http://127.0.0.1:8000/api/scanner/run/", {
        method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"
      })
      const d = await res.json()
      setCount(d.result?.signals || 0); setDone(true)
    } catch (_) {}
    setScanning(false)
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:8 }}>
      <button className="btn btn-primary" style={{ width:"100%", justifyContent:"flex-start" }}
        onClick={handleScan} disabled={scanning}>
        {scanning ? "⏳ กำลังสแกน..." : "▶ รัน Scanner ทันที"}
      </button>
      {done && <div style={{ fontSize:12, color:"var(--green)", padding:"4px 8px",
        background:"var(--green-dim)", borderRadius:6 }}>✅ พบ {count} สัญญาณ</div>}
      <button className="btn btn-ghost" style={{ width:"100%", justifyContent:"flex-start" }}
        onClick={() => fetch("http://127.0.0.1:8000/api/cache/warmup/",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})}>
        🔥 Warm-up Cache
      </button>
      <div style={{ borderTop:"1px solid var(--border)", paddingTop:8, marginTop:4 }}>
        <div style={{ fontSize:11, color:"var(--text-muted)" }}>อัปเดตอัตโนมัติทุกวัน จ–ศ</div>
        <div style={{ fontSize:11, color:"var(--text-muted)", marginTop:2 }}>
          18:00 หุ้นไทย · 23:00 Indicator · 23:30 Signal
        </div>
      </div>
    </div>
  )
}

// ── Main Dashboard ────────────────────────────────────────
export default function Dashboard({ onOpenChart }: { onOpenChart: (s: string) => void, ws: any }) {
  const [data, setData]         = useState<any>(null)
  const [tabData, setTabData]   = useState({ buy:[], sell:[], breakout:[], watch:[] } as Record<string,SignalInfo[]>)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState<string|null>(null)

  useEffect(() => {
    const BASE = "http://127.0.0.1:8000/api"
    setLoading(true)

    // โหลดทุกอย่างพร้อมกัน
    Promise.all([
      api.getDashboard(),
      fetch(`${BASE}/signals/?direction=LONG&days=7&page_size=50`).then(r=>r.json()),
      fetch(`${BASE}/signals/?direction=SHORT&days=7&page_size=50`).then(r=>r.json()),
      fetch(`${BASE}/signals/?signal_type=BREAKOUT&days=7&page_size=50`).then(r=>r.json()),
      fetch(`${BASE}/signals/?signal_type=WATCH&days=7&page_size=50`).then(r=>r.json()),
    ]).then(([dash, buyR, sellR, brkR, watchR]) => {
      setData(dash)
      setTabData({
        buy:      buyR.results   || [],
        sell:     sellR.results  || [],
        breakout: brkR.results   || [],
        watch:    watchR.results || [],
      })
    }).catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลดข้อมูล...</span></div>
  if (error)   return <div className="empty-state"><span>⚠️</span><span style={{ color:"var(--red)" }}>{error}</span></div>

  const stats  = data?.stats || {}
  const latest = data?.latest_signals || []

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📡 Radar หุ้น</div>
        <div className="page-subtitle">ภาพรวมตลาด · สัญญาณซื้อขายล่าสุด</div>
      </div>
      <div className="page-body">

        {/* ── Stats ── */}
        <div className="stats-grid" style={{ marginBottom:20 }}>
          {[
            { label:"หุ้นทั้งหมด",  val: stats.total_symbols,  color:"accent" },
            { label:"สัญญาณซื้อ",   val: stats.buy_signals,    color:"green"  },
            { label:"สัญญาณขาย",   val: stats.sell_signals,   color:"red"    },
            { label:"Breakout",    val: stats.breakout_count, color:"yellow" },
          ].map(({ label, val, color }) => (
            <div key={label} className={`stat-card ${color}`}>
              <div className="stat-label">{label}</div>
              <div className="stat-value">{(val||0).toLocaleString()}</div>
            </div>
          ))}
        </div>

        {/* ── Signal Tables (Tabs) ── */}
        <SignalTabs
          buyList={tabData.buy} sellList={tabData.sell}
          breakoutList={tabData.breakout} watchList={tabData.watch}
          stats={stats} onOpenChart={onOpenChart}
        />

        {/* ── Bottom Row ── */}
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 280px", gap:16, marginTop:16 }}>

          {/* Latest Signals */}
          <div className="card">
            <div className="card-title">🔔 สัญญาณล่าสุด</div>
            {latest.slice(0,10).map((s: SignalInfo, i: number) => (
              <div key={i} className="signal-item" onClick={() => onOpenChart(s.symbol_code)}
                style={{ cursor:"pointer" }}>
                <div className="signal-symbol">{s.symbol_code}</div>
                <div className="signal-info">
                  <Badge type={s.signal_type} />
                  <div className="signal-time" style={{ marginTop:3, fontSize:11 }}>
                    {s.exchange} · {formatTime(s.created_at)}
                  </div>
                </div>
                <div className="price-cell" style={{ textAlign:"right", fontFamily:"var(--font-mono)", fontSize:13 }}>
                  {s.price?.toLocaleString("th-TH",{minimumFractionDigits:2})}
                </div>
              </div>
            ))}
          </div>

          {/* Exchange breakdown */}
          <div className="card">
            <div className="card-title">🌏 สัญญาณตามตลาด</div>
            {["NYSE","NASDAQ","SET"].map(exch => {
              const cnt = latest.filter((s:SignalInfo) => s.exchange===exch).length
              return cnt > 0 ? (
                <div key={exch} style={{ marginBottom:12 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4, fontSize:13 }}>
                    <span style={{ fontWeight:600 }}>{exch}</span>
                    <span style={{ fontFamily:"var(--font-mono)", color:"var(--accent)" }}>{cnt}</span>
                  </div>
                  <div style={{ background:"var(--border)", borderRadius:2, height:4 }}>
                    <div style={{ background:"var(--accent)", borderRadius:2, height:"100%",
                      width:`${(cnt/Math.max(latest.length,1))*100}%` }} />
                  </div>
                </div>
              ) : null
            })}
          </div>

          {/* Quick Actions */}
          <div className="card">
            <div className="card-title">⚡ การดำเนินการด่วน</div>
            <QuickActions />
          </div>
        </div>

      </div>
    </div>
  )
}
