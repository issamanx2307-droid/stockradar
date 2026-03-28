import { useState, useEffect } from "react"
import { api } from "../api/client"
import { SignalInfo } from "../api/types"
import { TermText } from "../components/TermAssistant"

const SIGNAL_LABELS: Record<string, string> = {
  BUY: "โมเมนตัมบวก", STRONG_BUY: "โมเมนตัมบวกแรง", BREAKOUT: "Breakout",
  GOLDEN_CROSS: "Golden Cross", OVERSOLD: "Oversold",
  SELL: "โมเมนตัมลบ", STRONG_SELL: "โมเมนตัมลบแรง", DEATH_CROSS: "Death Cross",
  BREAKDOWN: "Breakdown", OVERBOUGHT: "Overbought",
  WATCH: "เฝ้าดู", ALERT: "แจ้งเตือน",
}
const SIGNAL_EMOJIS: Record<string, string> = {
  BUY: "🟢", STRONG_BUY: "💚", BREAKOUT: "🚀", GOLDEN_CROSS: "⭐", OVERSOLD: "🔵",
  SELL: "🔴", STRONG_SELL: "❤️", DEATH_CROSS: "💀", BREAKDOWN: "💥", OVERBOUGHT: "🟡",
  WATCH: "👁️", ALERT: "⚠️",
}

function formatDateTime(iso: string) {
  if (!iso) return "-"
  return new Date(iso).toLocaleString("th-TH", {
    year: "numeric", month: "short", day: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

function SignalBadge({ type }: { type: string }) {
  const cls = type?.toLowerCase()
  const label = SIGNAL_LABELS[type] || type
  return (
    <span className={`signal-badge ${cls}`}>
      {SIGNAL_EMOJIS[type] || "⬜"} <TermText text={label} />
    </span>
  )
}

export default function Signals({ onOpenChart }: { onOpenChart: (s: string) => void }) {
  const [signals, setSignals] = useState<SignalInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ signal_type: "", exchange: "", days: "30", min_score: "" })

  const loadSignals = () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filter.signal_type) params.signal_type = filter.signal_type
    if (filter.exchange) params.exchange = filter.exchange
    if (filter.days) params.days = filter.days
    if (filter.min_score) params.min_score = filter.min_score

    api.getSignals(params)
      .then(d => setSignals(d.results || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadSignals() }, [])

  const updateFilter = (key: string, val: string) => setFilter(f => ({ ...f, [key]: val }))

  // แบ่งกลุ่ม Bullish / Bearish / Neutral
  const bullish = signals.filter(s => ["BUY", "STRONG_BUY", "BREAKOUT", "GOLDEN_CROSS", "OVERSOLD"].includes(s.signal_type))
  const bearish = signals.filter(s => ["SELL", "STRONG_SELL", "DEATH_CROSS", "BREAKDOWN", "OVERBOUGHT"].includes(s.signal_type))

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">🔔 สัญญาณซื้อขาย</div>
        <div className="page-subtitle">รายการสัญญาณทั้งหมดจาก Signal Engine</div>
      </div>

      <div className="page-body">

        {/* ── Summary Cards ── */}
        <div className="stats-grid" style={{ marginBottom: 20 }}>
          <div className="stat-card green">
            <div className="stat-label">Bullish</div>
            <div className="stat-value">{bullish.length}</div>
          </div>
          <div className="stat-card red">
            <div className="stat-label">Bearish</div>
            <div className="stat-value">{bearish.length}</div>
          </div>
          <div className="stat-card accent">
            <div className="stat-label">ทั้งหมด</div>
            <div className="stat-value">{signals.length}</div>
          </div>
          <div className="stat-card yellow">
            <div className="stat-label">คะแนนเฉลี่ย</div>
            <div className="stat-value">
              {signals.length > 0 
                ? (signals.reduce((acc, r) => acc + (Number(r.score) || 0), 0) / signals.length).toFixed(0) 
                : "—"}
            </div>
          </div>
        </div>

        {/* ── Filters ── */}
        <div className="card" style={{ marginBottom: 18 }}>
          <div className="filters">
            <select className="filter-select" value={filter.signal_type}
              onChange={e => updateFilter("signal_type", e.target.value)}>
              <option value="">ทุกสัญญาณ</option>
              {Object.entries(SIGNAL_LABELS).map(([k, v]) => (
                <option key={k} value={k}>{SIGNAL_EMOJIS[k]} {v}</option>
              ))}
            </select>
            <select className="filter-select" value={filter.exchange}
              onChange={e => updateFilter("exchange", e.target.value)}>
              <option value="">ทุกตลาด</option>
              <option value="SET">🇹🇭 SET</option>
              <option value="NASDAQ">🇺🇸 NASDAQ</option>
              <option value="NYSE">🇺🇸 NYSE</option>
            </select>
            <select className="filter-select" value={filter.days}
              onChange={e => updateFilter("days", e.target.value)}>
              <option value="1">วันนี้</option>
              <option value="7">7 วัน</option>
              <option value="30">30 วัน</option>
              <option value="90">90 วัน</option>
            </select>
            <input className="filter-select" style={{ width: 100 }} placeholder="คะแนน ≥" type="number"
              value={filter.min_score} onChange={e => updateFilter("min_score", e.target.value)} />
            <button className="btn btn-primary" onClick={loadSignals}>🔍 กรอง</button>
          </div>
        </div>

        {/* ── Signal Table ── */}
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          {loading
            ? <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลด...</span></div>
            : signals.length === 0
              ? <div className="empty-state"><span style={{ fontSize: 32 }}>🔔</span><span>ไม่พบสัญญาณ</span></div>
              : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>หุ้น</th>
                      <th>ตลาด</th>
                      <th>สัญญาณ</th>
                      <th style={{ minWidth: 140 }}>คะแนน</th>
                      <th style={{ textAlign: "right" }}>ราคา</th>
                      <th>เวลา</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signals.map((s, i) => (
                      <tr key={i} onClick={() => onOpenChart(s.symbol_code)}>
                        <td>
                          <div className="symbol-cell">
                            <span className="symbol-code">{s.symbol_code}</span>
                            <span className="symbol-name">{s.symbol_name}</span>
                          </div>
                        </td>
                        <td>
                          <span style={{
                            background: "var(--bg-elevated)", borderRadius: 4,
                            padding: "2px 7px", fontSize: 11,
                            fontFamily: "var(--font-mono)", color: "var(--text-secondary)",
                          }}>{s.exchange}</span>
                        </td>
                        <td><SignalBadge type={s.signal_type} /></td>
                        <td>
                          <div className="score-bar">
                            <div className="score-bar-track">
                              <div className="score-bar-fill" style={{ width: `${s.score || 0}%` }} />
                            </div>
                            <span className="score-text">{Number(s.score).toFixed(0)}</span>
                          </div>
                        </td>
                        <td className="price-cell" style={{ textAlign: "right" }}>
                          {Number(s.price).toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                        </td>
                        <td style={{ fontSize: 12, color: "var(--text-secondary)", fontFamily: "var(--font-mono)", whiteSpace: "nowrap" }}>
                          {formatDateTime(s.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
          }
        </div>
      </div>
    </div>
  )
}
