/**
 * pages/EconomicCalendar.tsx
 * ปฏิทินเศรษฐกิจสัปดาห์นี้ — ForexFactory data · Cache 1h
 */
import { useState, useEffect } from "react"
import { API_BASE } from "../api/config"

interface CalEvent {
  datetime: string; date: string; time: string
  country: string; flag: string; event: string
  impact: string; impact_score: number
  forecast: string; previous: string; actual: string
}

const IMPACT_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  High:   { color: "#ff5252", bg: "rgba(255,82,82,0.15)",   label: "🔴 สูง" },
  Medium: { color: "#ffd600", bg: "rgba(255,214,0,0.12)",   label: "🟡 กลาง" },
  Low:    { color: "#78909c", bg: "rgba(120,144,156,0.1)",  label: "⚪ ต่ำ" },
}

function ImpactBadge({ impact }: { impact: string }) {
  const cfg = IMPACT_CONFIG[impact] || IMPACT_CONFIG.Low
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
      background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}44`,
      whiteSpace: "nowrap",
    }}>{cfg.label}</span>
  )
}

function ValueCell({ val, prev, forecast }: { val?: string; prev?: string; forecast?: string }) {
  if (!val && !prev && !forecast) return <span style={{ color: "var(--text-muted)" }}>—</span>
  const isUp = val && prev && parseFloat(val.replace(/[^0-9.-]/g, "")) > parseFloat(prev.replace(/[^0-9.-]/g, ""))
  const isDown = val && prev && parseFloat(val.replace(/[^0-9.-]/g, "")) < parseFloat(prev.replace(/[^0-9.-]/g, ""))
  return (
    <div style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
      {val ? (
        <span style={{ fontWeight: 700, color: isUp ? "var(--green)" : isDown ? "var(--red)" : "var(--text-primary)" }}>
          {val} {isUp ? "▲" : isDown ? "▼" : ""}
        </span>
      ) : (
        <span style={{ color: "var(--text-muted)" }}>—</span>
      )}
      {(forecast || prev) && (
        <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
          {forecast && <span>คาด: {forecast}</span>}
          {forecast && prev && <span> · </span>}
          {prev && <span>ก่อน: {prev}</span>}
        </div>
      )}
    </div>
  )
}

export default function EconomicCalendar() {
  const [events, setEvents]     = useState<CalEvent[]>([])
  const [byDate, setByDate]     = useState<Record<string, CalEvent[]>>({})
  const [loading, setLoading]   = useState(true)
  const [days, setDays]         = useState(7)
  const [impact, setImpact]     = useState("")  // filter: High, Medium, Low
  const [country, setCountry]   = useState("")  // filter: USD, EUR, etc.
  const [count, setCount]       = useState(0)

  useEffect(() => {
    setLoading(true)
    fetch(`${API_BASE}/calendar/?days=${days}`)
      .then(r => r.json())
      .then(d => {
        setCount(d.count || 0)
        const evs: CalEvent[] = d.events || []
        setEvents(evs)
        // group by date
        const grouped: Record<string, CalEvent[]> = {}
        evs.forEach(ev => {
          if (!grouped[ev.date]) grouped[ev.date] = []
          grouped[ev.date].push(ev)
        })
        setByDate(grouped)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days])

  const countries = [...new Set(events.map(e => e.country))].sort()

  const filtered = events.filter(ev => {
    if (impact  && ev.impact  !== impact)  return false
    if (country && ev.country !== country) return false
    return true
  })

  // group filtered by date
  const filteredByDate: Record<string, CalEvent[]> = {}
  filtered.forEach(ev => {
    if (!filteredByDate[ev.date]) filteredByDate[ev.date] = []
    filteredByDate[ev.date].push(ev)
  })

  const today = new Date().toISOString().slice(0, 10)
  const highCount = filtered.filter(e => e.impact === "High").length

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📅 ปฏิทินเศรษฐกิจ</div>
        <div className="page-subtitle">
          รายการเหตุการณ์เศรษฐกิจสำคัญ · ข้อมูลจาก ForexFactory · อัปเดตทุก 1 ชั่วโมง
        </div>
      </div>
      <div className="page-body">

        {/* Stats */}
        <div style={{ display:"flex", gap:12, marginBottom:20, flexWrap:"wrap" }}>
          {[
            { label:"เหตุการณ์ทั้งหมด", val: count,     color:"var(--accent)" },
            { label:"High Impact",      val: highCount, color:"var(--red)"    },
            { label:"วันที่แสดง",       val: days,      color:"var(--text-primary)" },
          ].map(({ label, val, color }) => (
            <div key={label} className="card" style={{ padding:"10px 16px", minWidth:120 }}>
              <div style={{ fontSize:11, color:"var(--text-muted)" }}>{label}</div>
              <div style={{ fontSize:22, fontWeight:700, fontFamily:"var(--font-mono)", color }}>{val}</div>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="card" style={{ marginBottom:20 }}>
          <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"center" }}>
            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>ช่วงเวลา</div>
              <div style={{ display:"flex", gap:4 }}>
                {[3,7,14].map(d => (
                  <button key={d} onClick={() => setDays(d)} style={{
                    padding:"5px 12px", borderRadius:6, fontSize:12, fontWeight:700, cursor:"pointer",
                    border:`1px solid ${days===d?"var(--accent)":"var(--border)"}`,
                    background: days===d?"var(--accent-dim)":"transparent",
                    color: days===d?"var(--accent)":"var(--text-muted)",
                  }}>{d} วัน</button>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>Impact</div>
              <div style={{ display:"flex", gap:4 }}>
                {["","High","Medium","Low"].map(v => (
                  <button key={v} onClick={() => setImpact(v)} style={{
                    padding:"5px 12px", borderRadius:6, fontSize:11, fontWeight:700, cursor:"pointer",
                    border:`1px solid ${impact===v?"var(--accent)":"var(--border)"}`,
                    background: impact===v?"var(--accent-dim)":"transparent",
                    color: impact===v?"var(--accent)":"var(--text-muted)",
                  }}>{v||"ทั้งหมด"}</button>
                ))}
              </div>
            </div>
            <div>
              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>สกุลเงิน</div>
              <select className="filter-select" value={country} onChange={e => setCountry(e.target.value)}>
                <option value="">ทั้งหมด</option>
                {countries.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            {(impact||country) && (
              <button className="btn btn-ghost" style={{ marginTop:18, fontSize:11 }}
                onClick={() => { setImpact(""); setCountry("") }}>✕ ล้าง</button>
            )}
            <span style={{ marginLeft:"auto", fontSize:12, color:"var(--text-muted)", marginTop:18 }}>
              แสดง {filtered.length} จาก {count} รายการ
            </span>
          </div>
        </div>

        {/* Calendar */}
        {loading ? (
          <div className="loading-state"><div className="loading-spinner"/><span>กำลังโหลดปฏิทิน...</span></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize:48 }}>📅</span>
            <span>ไม่พบเหตุการณ์ที่ตรงเงื่อนไข</span>
          </div>
        ) : (
          Object.entries(filteredByDate).map(([date, evs]) => {
            const isToday = date === today
            const dateObj = new Date(date)
            const dateLabel = dateObj.toLocaleDateString("th-TH", {
              weekday:"long", year:"numeric", month:"long", day:"numeric"
            })
            const highImpactCount = evs.filter(e => e.impact === "High").length

            return (
              <div key={date} style={{ marginBottom:20 }}>
                {/* Date header */}
                <div style={{
                  display:"flex", alignItems:"center", gap:12, marginBottom:8,
                  padding:"8px 16px", borderRadius:8,
                  background: isToday ? "rgba(0,212,255,0.08)" : "var(--bg-elevated)",
                  border: `1px solid ${isToday?"var(--accent)":"var(--border)"}`,
                }}>
                  <span style={{ fontWeight:700, fontSize:14, color: isToday?"var(--accent)":"var(--text-primary)" }}>
                    {isToday ? "🔵 วันนี้ — " : ""}{dateLabel}
                  </span>
                  {highImpactCount > 0 && (
                    <span style={{ fontSize:11, padding:"1px 8px", borderRadius:10,
                      background:"rgba(255,82,82,0.15)", color:"var(--red)", fontWeight:700 }}>
                      🔴 High: {highImpactCount}
                    </span>
                  )}
                  <span style={{ marginLeft:"auto", fontSize:11, color:"var(--text-muted)" }}>
                    {evs.length} รายการ
                  </span>
                </div>

                {/* Events table */}
                <div style={{ background:"var(--bg-surface)", border:"1px solid var(--border)", borderRadius:8, overflow:"hidden" }}>
                  <table className="data-table" style={{ fontSize:13 }}>
                    <thead>
                      <tr>
                        <th style={{ width:90, paddingLeft:16 }}>เวลา (UTC)</th>
                        <th style={{ width:80 }}>ประเทศ</th>
                        <th>เหตุการณ์</th>
                        <th style={{ width:100 }}>Impact</th>
                        <th style={{ textAlign:"right", width:140, paddingRight:16 }}>จริง / คาด / ก่อน</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evs.map((ev, i) => {
                        const isPast = new Date(ev.datetime) < new Date()
                        const isHigh = ev.impact === "High"
                        return (
                          <tr key={i} style={{
                            background: isHigh && !isPast ? "rgba(255,82,82,0.04)" : undefined,
                            opacity: isPast ? 0.6 : 1,
                          }}>
                            <td style={{ paddingLeft:16, fontFamily:"var(--font-mono)", fontSize:12, color:"var(--text-muted)" }}>
                              {ev.time}
                              {isPast && <div style={{ fontSize:10, color:"var(--text-muted)" }}>ผ่านแล้ว</div>}
                            </td>
                            <td>
                              <span style={{ fontSize:16 }}>{ev.flag}</span>
                              <span style={{ fontSize:11, fontFamily:"var(--font-mono)", marginLeft:4, color:"var(--text-muted)" }}>
                                {ev.country}
                              </span>
                            </td>
                            <td style={{ fontWeight: isHigh ? 700 : 400 }}>
                              {ev.event}
                            </td>
                            <td><ImpactBadge impact={ev.impact}/></td>
                            <td style={{ textAlign:"right", paddingRight:16 }}>
                              <ValueCell val={ev.actual} prev={ev.previous} forecast={ev.forecast}/>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
