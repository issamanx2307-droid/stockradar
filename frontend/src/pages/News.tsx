import { useState, useEffect, useCallback } from "react"

const BASE = (import.meta as any).env.VITE_API_URL || "http://127.0.0.1:8000/api"

const SENTIMENT_CONFIG = {
  BULLISH: { label: "🟢 Bullish", color: "var(--green)",  bg: "rgba(0,230,118,0.1)" },
  BEARISH: { label: "🔴 Bearish", color: "var(--red)",    bg: "rgba(255,82,82,0.1)"  },
  NEUTRAL: { label: "⚪ Neutral", color: "var(--text-muted)", bg: "var(--bg-elevated)" },
}
const SOURCE_FLAG: Record<string, string> = {
  SET: "🇹🇭", REUTERS: "🌐", YAHOO: "💹", GOOGLE: "🔍",
  THANSETTAKIJ: "🇹🇭", MANAGER: "🇹🇭", BANGKOKPOST: "🇹🇭", OTHER: "📰",
}

// ── Category color by economic category ──────────────────────────────────────
const CATEGORY_COLOR: Record<string, string> = {
  monetary: "var(--accent)",
  price:    "#f59e0b",
  growth:   "var(--green)",
  forex:    "#a78bfa",
  trade:    "#38bdf8",
  tourism:  "#fb7185",
  labor:    "#94a3b8",
}

interface NewsItem {
  id: number; title: string; summary: string; url: string
  source: string; published_at: string
  sentiment: "BULLISH" | "BEARISH" | "NEUTRAL"
  sentiment_score: number; symbols: string[]
}

interface SentimentSummary {
  total: number; bullish: number; bearish: number; neutral: number; avg_score: number | null
}

interface ThaiIndicator {
  id: string; name: string; name_en: string
  value: string; unit: string
  prev_value: string; change: string; trend: "up" | "down" | "neutral"
  period: string; icon: string; category: string
  source: string; description: string
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)  return "เพิ่งเมื่อกี้"
  if (m < 60) return `${m} นาทีที่แล้ว`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h} ชั่วโมงที่แล้ว`
  return `${Math.floor(h / 24)} วันที่แล้ว`
}

function SentimentBar({ summary }: { summary: SentimentSummary }) {
  if (!summary?.total) return null
  const { total, bullish, bearish, neutral } = summary
  const bPct = Math.round((bullish / total) * 100)
  const rPct = Math.round((bearish / total) * 100)
  const nPct = 100 - bPct - rPct
  const score = summary.avg_score ?? 0
  const label = score > 0.1 ? "🟢 Bullish" : score < -0.1 ? "🔴 Bearish" : "⚪ Neutral"
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="card-title">📊 Market Sentiment — {total} ข่าว</div>
      <div style={{ display: "flex", gap: 16, marginBottom: 10, flexWrap: "wrap" }}>
        {[
          { label: "🟢 Bullish", val: bullish, pct: bPct, c: "var(--green)" },
          { label: "🔴 Bearish", val: bearish, pct: rPct, c: "var(--red)"   },
          { label: "⚪ Neutral", val: neutral, pct: nPct, c: "var(--text-muted)" },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, minWidth: 100, textAlign: "center",
            background: "var(--bg-elevated)", borderRadius: 8, padding: "10px 8px" }}>
            <div style={{ fontSize: 20, fontWeight: 700, color: s.c }}>{s.val}</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{s.label} ({s.pct}%)</div>
          </div>
        ))}
        <div style={{ flex: 1, minWidth: 100, textAlign: "center",
          background: "var(--bg-elevated)", borderRadius: 8, padding: "10px 8px" }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>{label}</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>ภาพรวมตลาด</div>
        </div>
      </div>
      <div style={{ height: 8, borderRadius: 4, overflow: "hidden", display: "flex" }}>
        <div style={{ width: `${bPct}%`, background: "var(--green)", transition: "width 0.5s" }} />
        <div style={{ width: `${nPct}%`, background: "var(--border)" }} />
        <div style={{ width: `${rPct}%`, background: "var(--red)", transition: "width 0.5s" }} />
      </div>
    </div>
  )
}

// ── Thai Economic Indicators Tab ──────────────────────────────────────────────
function ThaiIndicatorsTab() {
  const [indicators, setIndicators] = useState<ThaiIndicator[]>([])
  const [updatedAt, setUpdatedAt] = useState("")
  const [note, setNote] = useState("")
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    fetch(`${BASE}/thai-indicators/`)
      .then(r => r.json())
      .then(d => {
        setIndicators(d.indicators || [])
        setUpdatedAt(d.updated_at || "")
        setNote(d.note || "")
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลดข้อมูล...</span></div>
  )

  const trendIcon = (t: string) => t === "up" ? "▲" : t === "down" ? "▼" : "—"
  const trendColor = (t: string) =>
    t === "up" ? "var(--green)" : t === "down" ? "var(--red)" : "var(--text-muted)"

  // Group by category for display order
  const categories = [
    { key: "monetary", label: "นโยบายการเงิน" },
    { key: "price",    label: "ราคา & เงินเฟ้อ" },
    { key: "growth",   label: "การเติบโต" },
    { key: "forex",    label: "อัตราแลกเปลี่ยน" },
    { key: "trade",    label: "การค้าระหว่างประเทศ" },
    { key: "tourism",  label: "การท่องเที่ยว" },
    { key: "labor",    label: "ตลาดแรงงาน" },
  ]

  return (
    <div>
      {/* Header Info */}
      <div className="card" style={{ marginBottom: 16, padding: "12px 16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: "var(--text-primary)" }}>
              🏦 ตัวชี้วัดเศรษฐกิจไทย (Thai Macroeconomic Indicators)
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>
              ข้อมูลจากแหล่งราชการ: BOT · สภาพัฒน์ · กรมการค้าภายใน · กรมศุลกากร · สำนักงานสถิติแห่งชาติ
            </div>
          </div>
          {updatedAt && (
            <div style={{ fontSize: 11, color: "var(--text-muted)", textAlign: "right" }}>
              อัปเดต: {updatedAt}
            </div>
          )}
        </div>
        {note && (
          <div style={{ marginTop: 8, fontSize: 11, color: "var(--text-muted)",
            padding: "6px 10px", background: "var(--bg-elevated)", borderRadius: 6 }}>
            ℹ️ {note}
          </div>
        )}
      </div>

      {/* Indicator Cards Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
        {indicators.map(ind => {
          const catColor = CATEGORY_COLOR[ind.category] || "var(--accent)"
          const isExpanded = expanded === ind.id
          const changeNum = parseFloat(ind.change)
          const changePositive = changeNum > 0

          return (
            <div key={ind.id} className="card" style={{
              padding: 0, overflow: "hidden", cursor: "pointer",
              borderTop: `3px solid ${catColor}`,
              transition: "transform 0.15s, box-shadow 0.15s",
            }}
              onClick={() => setExpanded(isExpanded ? null : ind.id)}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)" }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = "none" }}
            >
              <div style={{ padding: "14px 16px" }}>
                {/* Top row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 22 }}>{ind.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.3 }}>
                        {ind.name}
                      </div>
                      <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{ind.name_en}</div>
                    </div>
                  </div>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{isExpanded ? "▲" : "▼"}</span>
                </div>

                {/* Value row */}
                <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 6 }}>
                  <div style={{ fontSize: 26, fontWeight: 800, color: catColor, fontFamily: "var(--font-mono)" }}>
                    {ind.value}
                  </div>
                  <div style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 600 }}>{ind.unit}</div>
                </div>

                {/* Change row */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: trendColor(ind.trend),
                      fontFamily: "var(--font-mono)" }}>
                      {trendIcon(ind.trend)} {changePositive ? "+" : ""}{ind.change}
                    </span>
                    <span style={{ fontSize: 10, color: "var(--text-muted)" }}>จาก {ind.prev_value}</span>
                  </div>
                  <span style={{ fontSize: 10, padding: "2px 7px", borderRadius: 8,
                    background: "var(--bg-elevated)", color: "var(--text-muted)" }}>
                    {ind.period}
                  </span>
                </div>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div style={{ padding: "10px 16px 14px", borderTop: "1px solid var(--border)",
                  background: "var(--bg-elevated)" }}>
                  <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "0 0 6px",
                    lineHeight: 1.6 }}>
                    {ind.description}
                  </p>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    📌 แหล่งข้อมูล: {ind.source}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {indicators.length === 0 && (
        <div className="empty-state">
          <span style={{ fontSize: 48 }}>🏦</span>
          <span>ไม่พบข้อมูลตัวชี้วัด</span>
        </div>
      )}
    </div>
  )
}

// ── Main News Component ───────────────────────────────────────────────────────
export default function News({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [tab, setTab] = useState<"news" | "indicators">("news")
  const [news, setNews] = useState<NewsItem[]>([])
  const [summary, setSummary] = useState<SentimentSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [filter, setFilter] = useState<"ALL" | "BULLISH" | "BEARISH" | "NEUTRAL">("ALL")
  const [days, setDays] = useState(3)
  const [search, setSearch] = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ days: String(days), limit: "100" })
      if (filter !== "ALL") params.set("sentiment", filter)
      const res = await fetch(`${BASE}/news/?${params}`)
      const data = await res.json()
      setNews(data.results || [])
      setSummary(data.summary || null)
    } catch (e) { console.error(e) }
    setLoading(false)
  }, [days, filter])

  useEffect(() => { if (tab === "news") load() }, [load, tab])

  async function handleFetch() {
    setFetching(true)
    try {
      await fetch(`${BASE}/news/fetch/`, { method: "POST",
        headers: { "Content-Type": "application/json" } })
      await load()
    } catch (e) { console.error(e) }
    setFetching(false)
  }

  const filtered = news.filter(n =>
    !search || n.title.toLowerCase().includes(search.toLowerCase()) ||
    n.symbols.some(s => s.includes(search.toUpperCase()))
  )

  // ── Tab button style helper ──
  const tabStyle = (active: boolean) => ({
    padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer",
    border: `1.5px solid ${active ? "var(--accent)" : "var(--border)"}`,
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--accent)" : "var(--text-muted)",
    transition: "all 0.15s",
  })

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📰 ข่าว & ตัวชี้วัดเศรษฐกิจ</div>
        <div className="page-subtitle">ข่าวหุ้น · Sentiment · ตัวชี้วัดเศรษฐกิจไทย</div>
      </div>
      <div className="page-body">

        {/* ── Tab Navigation ── */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button style={tabStyle(tab === "news")} onClick={() => setTab("news")}>
            📰 ข่าวหุ้น & Sentiment
          </button>
          <button style={tabStyle(tab === "indicators")} onClick={() => setTab("indicators")}>
            🏦 ตัวชี้วัดเศรษฐกิจไทย
          </button>
        </div>

        {/* ── Tab: ข่าวหุ้น ── */}
        {tab === "news" && (
          <>
            {summary && <SentimentBar summary={summary} />}

            <div className="card" style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                <input className="filter-input" placeholder="🔍 ค้นหาข่าว หรือรหัสหุ้น..."
                  value={search} onChange={e => setSearch(e.target.value)}
                  style={{ flex: 1, minWidth: 200 }} />

                <div style={{ display: "flex", gap: 4 }}>
                  {(["ALL", "BULLISH", "BEARISH", "NEUTRAL"] as const).map(f => (
                    <button key={f} onClick={() => setFilter(f)} style={{
                      padding: "6px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600,
                      cursor: "pointer", transition: "all 0.15s",
                      border: `1px solid ${filter === f ? (f === "BULLISH" ? "var(--green)" : f === "BEARISH" ? "var(--red)" : "var(--accent)") : "var(--border)"}`,
                      background: filter === f ? (f === "BULLISH" ? "rgba(0,230,118,0.15)" : f === "BEARISH" ? "rgba(255,82,82,0.15)" : "var(--accent-dim)") : "transparent",
                      color: filter === f ? (f === "BULLISH" ? "var(--green)" : f === "BEARISH" ? "var(--red)" : "var(--accent)") : "var(--text-muted)",
                    }}>
                      {f === "ALL" ? "ทั้งหมด" : SENTIMENT_CONFIG[f].label}
                    </button>
                  ))}
                </div>

                <div style={{ display: "flex", gap: 4 }}>
                  {[1, 3, 7].map(d => (
                    <button key={d} onClick={() => setDays(d)} style={{
                      padding: "6px 10px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer",
                      border: `1px solid ${days === d ? "var(--accent)" : "var(--border)"}`,
                      background: days === d ? "var(--accent-dim)" : "transparent",
                      color: days === d ? "var(--accent)" : "var(--text-muted)",
                    }}>{d} วัน</button>
                  ))}
                </div>

                <button className="btn btn-primary" onClick={handleFetch} disabled={fetching}
                  style={{ padding: "8px 16px", fontSize: 12 }}>
                  {fetching ? "⏳ กำลังดึง..." : "🔄 ดึงข่าวใหม่"}
                </button>
              </div>
            </div>

            {loading
              ? <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลดข่าว...</span></div>
              : filtered.length === 0
                ? <div className="empty-state">
                    <span style={{ fontSize: 48 }}>📰</span>
                    <span>ยังไม่มีข่าว — กด "ดึงข่าวใหม่" เพื่อโหลด</span>
                  </div>
                : <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {filtered.map(n => {
                      const s = SENTIMENT_CONFIG[n.sentiment]
                      return (
                        <div key={n.id} className="card" style={{
                          padding: "14px 16px", borderLeft: `3px solid ${s.color}`,
                          transition: "transform 0.15s",
                        }}
                          onMouseEnter={e => (e.currentTarget.style.transform = "translateX(3px)")}
                          onMouseLeave={e => (e.currentTarget.style.transform = "none")}
                        >
                          <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                            <div style={{ flex: 1 }}>
                              <div style={{ display: "flex", gap: 8, marginBottom: 5, flexWrap: "wrap", alignItems: "center" }}>
                                <span style={{ fontSize: 13 }}>{SOURCE_FLAG[n.source] || "📰"}</span>
                                <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600 }}>{n.source}</span>
                                <span style={{ fontSize: 11, padding: "1px 8px", borderRadius: 10,
                                  background: s.bg, color: s.color, fontWeight: 700 }}>{s.label}</span>
                                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{timeAgo(n.published_at)}</span>
                              </div>
                              <a href={n.url} target="_blank" rel="noreferrer"
                                style={{ color: "var(--text-primary)", textDecoration: "none", fontWeight: 600,
                                  fontSize: 14, lineHeight: 1.5, display: "block", marginBottom: 4 }}>
                                {n.title}
                              </a>
                              {n.summary && (
                                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0,
                                  lineHeight: 1.6, display: "-webkit-box", WebkitLineClamp: 2,
                                  WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                                  {n.summary}
                                </p>
                              )}
                              {n.symbols.length > 0 && (
                                <div style={{ display: "flex", gap: 4, marginTop: 8, flexWrap: "wrap" }}>
                                  {n.symbols.map(sym => (
                                    <button key={sym} onClick={() => onOpenChart?.(sym)} style={{
                                      fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4,
                                      background: "var(--accent-dim)", color: "var(--accent)",
                                      border: "1px solid var(--accent)", cursor: "pointer",
                                      fontFamily: "var(--font-mono)",
                                    }}>{sym}</button>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div style={{ textAlign: "right", minWidth: 50 }}>
                              <div style={{ fontSize: 16, fontWeight: 700,
                                color: n.sentiment_score > 0 ? "var(--green)" : n.sentiment_score < 0 ? "var(--red)" : "var(--text-muted)" }}>
                                {n.sentiment_score > 0 ? "+" : ""}{n.sentiment_score.toFixed(2)}
                              </div>
                              <div style={{ fontSize: 10, color: "var(--text-muted)" }}>score</div>
                            </div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
            }
          </>
        )}

        {/* ── Tab: ตัวชี้วัดเศรษฐกิจไทย ── */}
        {tab === "indicators" && <ThaiIndicatorsTab />}

      </div>
    </div>
  )
}
