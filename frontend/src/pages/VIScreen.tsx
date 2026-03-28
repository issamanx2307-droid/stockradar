import { useState, useEffect, useCallback } from "react"
import { API_BASE } from "../api/config"

// ── Types ──────────────────────────────────────────────────────────────────
interface VIStock {
  symbol: string
  name: string
  exchange: string
  sector: string | null
  vi_score: number | null
  vi_grade: string | null
  pe_ratio: number | null
  pb_ratio: number | null
  roe: number | null
  roa: number | null
  net_margin: number | null
  revenue_growth: number | null
  debt_to_equity: number | null
  current_ratio: number | null
  dividend_yield: number | null
  market_cap: number | null
  fetched_at: string | null
}

interface VIResponse {
  count: number
  grade_counts: Record<string, number>
  results: VIStock[]
  fetching: boolean
}

interface FilterState {
  grade: string
  min_score: string
  max_pe: string
  max_pb: string
  min_roe: string
  min_div: string
  sort: string
}

const DEFAULT_FILTER: FilterState = {
  grade: "", min_score: "", max_pe: "", max_pb: "",
  min_roe: "", min_div: "", sort: "vi_score",
}

// ── Helpers ────────────────────────────────────────────────────────────────
function gradeColor(grade: string | null): string {
  if (grade === "A") return "#00c853"
  if (grade === "B") return "var(--green)"
  if (grade === "C") return "var(--yellow)"
  return "var(--red)"
}

function scoreColor(score: number | null): string {
  if (score === null) return "var(--text-muted)"
  if (score >= 80) return "#00c853"
  if (score >= 60) return "var(--green)"
  if (score >= 40) return "var(--yellow)"
  return "var(--red)"
}

function fmt(val: number | null, decimals = 1): string {
  if (val === null || val === undefined) return "-"
  return val.toFixed(decimals)
}

function fmtCap(cap: number | null): string {
  if (!cap) return "-"
  if (cap >= 1e12) return `${(cap / 1e12).toFixed(1)}T`
  if (cap >= 1e9)  return `${(cap / 1e9).toFixed(1)}B`
  if (cap >= 1e6)  return `${(cap / 1e6).toFixed(0)}M`
  return cap.toLocaleString()
}

// ── Grade Badge ────────────────────────────────────────────────────────────
function GradeBadge({ grade, score }: { grade: string | null; score: number | null }) {
  const color = gradeColor(grade)
  const label = grade === "A" ? "A ดีมาก" : grade === "B" ? "B ดี" : grade === "C" ? "C พอใช้" : grade === "D" ? "D อ่อน" : "-"
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "3px 10px", borderRadius: 6, fontSize: 12, fontWeight: 700,
      background: `${color}18`, color, border: `1px solid ${color}44`,
    }}>
      {score !== null ? score.toFixed(0) : "-"} · {label}
    </span>
  )
}

// ── Score Legend ───────────────────────────────────────────────────────────
function ScoreLegend() {
  return (
    <div style={{
      display: "flex", gap: 16, alignItems: "center",
      padding: "6px 14px", background: "var(--bg-elevated)",
      border: "1px solid var(--border)", borderRadius: 8,
      fontSize: 11, flexWrap: "wrap", marginBottom: 12,
    }}>
      <span style={{ color: "var(--text-muted)", fontWeight: 600 }}>VI Score:</span>
      {([
        { range: "A ≥80", label: "ดีมาก — น่าซื้อมาก", color: "#00c853" },
        { range: "B 60–79", label: "ดี — น่าพิจารณา",  color: "var(--green)" },
        { range: "C 40–59", label: "พอใช้ — ระวัง",    color: "var(--yellow)" },
        { range: "D <40",   label: "อ่อน — หลีกเลี่ยง", color: "var(--red)" },
      ] as const).map(({ range, label, color }) => (
        <span key={range} style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: color, display: "inline-block" }} />
          <span style={{ color }}><b>{range}</b> {label}</span>
        </span>
      ))}
    </div>
  )
}

// ── Filter Bar ─────────────────────────────────────────────────────────────
function FilterBar({
  filter, onChange, onApply, onClear,
}: {
  filter: FilterState
  onChange: (k: keyof FilterState, v: string) => void
  onApply: () => void
  onClear: () => void
}) {
  const sel = (k: keyof FilterState, opts: { v: string; l: string }[], placeholder = "") => (
    <select
      className="filter-select" style={{ fontSize: 11 }}
      value={filter[k]}
      onChange={e => onChange(k, e.target.value)}
    >
      <option value="">{placeholder}</option>
      {opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
    </select>
  )

  const num = (k: keyof FilterState, ph: string) => (
    <input
      className="filter-select" style={{ width: 90, fontSize: 11 }}
      type="number" placeholder={ph}
      value={filter[k]}
      onChange={e => onChange(k, e.target.value)}
    />
  )

  const isDirty = Object.entries(filter).some(([k, v]) => v !== (DEFAULT_FILTER as any)[k])

  return (
    <div style={{
      background: "var(--bg-elevated)", border: "1px solid var(--border)",
      borderRadius: "0 0 0 0", padding: "10px 14px",
      display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center",
    }}>
      {sel("grade", [
        { v: "A", l: "⭐ Grade A — ดีมาก (≥80)" },
        { v: "B", l: "✅ Grade B — ดี (60–79)" },
        { v: "C", l: "⚠️ Grade C — พอใช้ (40–59)" },
        { v: "D", l: "❌ Grade D — อ่อน (<40)" },
      ], "ทุก Grade")}
      {num("min_score", "Score ≥")}
      {num("max_pe",    "P/E ≤")}
      {num("max_pb",    "P/B ≤")}
      {num("min_roe",   "ROE ≥ %")}
      {num("min_div",   "ปันผล ≥ %")}
      {sel("sort", [
        { v: "vi_score",      l: "เรียงตาม VI Score" },
        { v: "pe_ratio",      l: "เรียงตาม P/E (ต่ำ→สูง)" },
        { v: "pb_ratio",      l: "เรียงตาม P/B (ต่ำ→สูง)" },
        { v: "roe",           l: "เรียงตาม ROE (สูง→ต่ำ)" },
        { v: "dividend_yield",l: "เรียงตาม ปันผล (สูง→ต่ำ)" },
      ], "")}
      <button className="btn btn-primary" style={{ fontSize: 11, padding: "5px 14px", height: 30 }} onClick={onApply}>
        กรอง
      </button>
      {isDirty && (
        <button className="btn btn-ghost" style={{ fontSize: 11, padding: "5px 10px", height: 30 }} onClick={onClear}>
          ✕ ล้าง
        </button>
      )}
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────────────────
export default function VIScreen({ onOpenChart }: { onOpenChart: (s: string) => void }) {
  const [data, setData]       = useState<VIResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter]   = useState<FilterState>(DEFAULT_FILTER)
  const [applied, setApplied] = useState<FilterState>(DEFAULT_FILTER)

  const load = useCallback((f: FilterState) => {
    setLoading(true)
    const p = new URLSearchParams()
    if (f.grade)     p.set("grade",     f.grade)
    if (f.min_score) p.set("min_score", f.min_score)
    if (f.max_pe)    p.set("max_pe",    f.max_pe)
    if (f.max_pb)    p.set("max_pb",    f.max_pb)
    if (f.min_roe)   p.set("min_roe",   f.min_roe)
    if (f.min_div)   p.set("min_div",   f.min_div)
    if (f.sort)      p.set("sort",      f.sort)
    p.set("page_size", "100")

    fetch(`${API_BASE}/vi-screen/?${p}`, {})
      .then(r => r.json())
      .then(d => setData(d))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load(applied) }, [load, applied])

  function setF(k: keyof FilterState, v: string) {
    setFilter(f => ({ ...f, [k]: v }))
  }

  const gradeCounts = data?.grade_counts ?? {}

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">💎 หุ้น VI</div>
        <div className="page-subtitle">VI Screener · คัดหุ้น SET คุณภาพสูงด้วยเกณฑ์ Value Investing</div>
      </div>

      <div className="page-body">

        {/* ── Grade Summary ── */}
        <div className="stats-grid" style={{ marginBottom: 16 }}>
          {[
            { grade: "A", label: "Grade A", sub: "ดีมาก ≥80", color: "#00c853" },
            { grade: "B", label: "Grade B", sub: "ดี 60–79",  color: "var(--green)" },
            { grade: "C", label: "Grade C", sub: "พอใช้ 40–59", color: "var(--yellow)" },
            { grade: "D", label: "Grade D", sub: "อ่อน <40",  color: "var(--red)" },
          ].map(({ grade, label, sub, color }) => (
            <div
              key={grade}
              className="stat-card"
              style={{ cursor: "pointer", borderColor: applied.grade === grade ? color : undefined }}
              onClick={() => {
                const next = applied.grade === grade ? "" : grade
                const newF = { ...applied, grade: next }
                setFilter(newF)
                setApplied(newF)
              }}
            >
              <div className="stat-label" style={{ color }}>{label}</div>
              <div className="stat-value" style={{ color }}>{gradeCounts[grade] ?? 0}</div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>
            </div>
          ))}
          <div className="stat-card">
            <div className="stat-label">รวมทั้งหมด</div>
            <div className="stat-value">{data?.count ?? 0}</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>หุ้นที่มีข้อมูล</div>
          </div>
        </div>

        {/* ── Filter + Table ── */}
        <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>

          {/* Tab header */}
          <div style={{
            padding: "12px 16px", borderBottom: "1px solid var(--border)",
            display: "flex", alignItems: "center", justifyContent: "space-between",
          }}>
            <span style={{ fontWeight: 700, fontSize: 14 }}>📊 ผลการค้นหา</span>
            {data && !data.fetching && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                {loading ? "⏳ กำลังกรอง..." : `${data.results.length} รายการ`}
              </span>
            )}
          </div>

          <FilterBar
            filter={filter}
            onChange={setF}
            onApply={() => setApplied(filter)}
            onClear={() => { setFilter(DEFAULT_FILTER); setApplied(DEFAULT_FILTER) }}
          />

          <ScoreLegend />

          {/* Fetching notice */}
          {data?.fetching && (
            <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
              <div style={{ fontSize: 24, marginBottom: 8 }}>⏳</div>
              <p>กำลังดึงข้อมูล Fundamental จาก Yahoo Finance...</p>
              <p style={{ fontSize: 11, marginTop: 4 }}>ใช้เวลาประมาณ 2–3 นาที กรุณากลับมาตรวจสอบใหม่</p>
            </div>
          )}

          {/* Loading */}
          {loading && !data?.fetching && (
            <div className="loading-state" style={{ height: 300 }}>
              <div className="loading-spinner" />
              <span>กำลังโหลด...</span>
            </div>
          )}

          {/* Table */}
          {!loading && data && !data.fetching && (
            data.results.length === 0
              ? <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)", fontSize: 13 }}>ไม่พบหุ้นที่ตรงเงื่อนไข</div>
              : (
                <div style={{ overflowX: "auto" }}>
                  <table className="data-table" style={{ fontSize: 12 }}>
                    <thead>
                      <tr>
                        <th style={{ paddingLeft: 16 }}>หุ้น</th>
                        <th style={{ textAlign: "center" }}>VI Score</th>
                        <th style={{ textAlign: "right" }}>P/E</th>
                        <th style={{ textAlign: "right" }}>P/B</th>
                        <th style={{ textAlign: "right" }}>ROE %</th>
                        <th style={{ textAlign: "right" }}>D/E</th>
                        <th style={{ textAlign: "right" }}>ปันผล %</th>
                        <th style={{ textAlign: "right" }}>รายได้ YoY</th>
                        <th style={{ textAlign: "right", paddingRight: 16 }}>Mkt Cap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.results.map(s => (
                        <tr
                          key={s.symbol}
                          onClick={() => onOpenChart(s.symbol)}
                          style={{ cursor: "pointer" }}
                        >
                          <td style={{ paddingLeft: 16 }}>
                            <div style={{ display: "flex", flexDirection: "column" }}>
                              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 13, color: "var(--accent)" }}>
                                {s.symbol}
                              </span>
                              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{s.name}</span>
                            </div>
                          </td>
                          <td style={{ textAlign: "center" }}>
                            <GradeBadge grade={s.vi_grade} score={s.vi_score} />
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: s.pe_ratio !== null && s.pe_ratio <= 15 ? "var(--green)" : undefined }}>
                            {fmt(s.pe_ratio)}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: s.pb_ratio !== null && s.pb_ratio <= 1.5 ? "var(--green)" : undefined }}>
                            {fmt(s.pb_ratio)}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: s.roe !== null && s.roe >= 15 ? "var(--green)" : s.roe !== null && s.roe < 0 ? "var(--red)" : undefined }}>
                            {fmt(s.roe)}%
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: s.debt_to_equity !== null && s.debt_to_equity > 2 ? "var(--red)" : undefined }}>
                            {fmt(s.debt_to_equity)}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: s.dividend_yield !== null && s.dividend_yield >= 3 ? "var(--green)" : undefined }}>
                            {s.dividend_yield !== null ? `${fmt(s.dividend_yield)}%` : "-"}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: s.revenue_growth !== null && s.revenue_growth >= 10 ? "var(--green)" : s.revenue_growth !== null && s.revenue_growth < 0 ? "var(--red)" : undefined }}>
                            {s.revenue_growth !== null ? `${fmt(s.revenue_growth)}%` : "-"}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-muted)", paddingRight: 16 }}>
                            {fmtCap(s.market_cap)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
          )}
        </div>

        {/* ── Methodology note ── */}
        <div style={{
          marginTop: 16, padding: "12px 16px",
          background: "var(--bg-elevated)", border: "1px solid var(--border)",
          borderRadius: 8, fontSize: 11, color: "var(--text-muted)",
        }}>
          <b>วิธีคำนวณ VI Score (0–100):</b>{" "}
          P/E (25pt) + P/B (20pt) + ROE (20pt) + ปันผล (15pt) + D/E (10pt) + รายได้ YoY (10pt){" "}
          · ข้อมูลจาก Yahoo Finance · อัปเดตทุก 7 วัน
        </div>

      </div>
    </div>
  )
}
