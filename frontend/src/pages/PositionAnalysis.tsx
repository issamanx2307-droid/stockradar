import { useState } from "react"
import { api } from "../api/client"

type PositionAnalysisResponse = {
  symbol: string
  buy_price: number
  market_price: number
  pnl_pct: number
  indicators: {
    rsi14: number | null
    ema20: number | null
    ema50: number | null
    ema200: number | null
    adx14: number | null
  }
  decision: "BUY_MORE" | "HOLD" | "SELL"
  score: number
  confidence: number
  explanation: string
  signals: Record<string, any>
  analysis_id: number
}

function decisionLabel(d: PositionAnalysisResponse["decision"]) {
  if (d === "BUY_MORE") return "สัญญาณสนับสนุนฝั่งบวก (BUY_MORE)"
  if (d === "SELL") return "สัญญาณเตือนความเสี่ยง (SELL)"
  return "สัญญาณก้ำกึ่ง (HOLD)"
}

function badgeColor(d: PositionAnalysisResponse["decision"]) {
  if (d === "BUY_MORE") return "var(--green)"
  if (d === "SELL") return "var(--red)"
  return "var(--yellow)"
}

export default function PositionAnalysis() {
  const [symbol, setSymbol] = useState("")
  const [buyPrice, setBuyPrice] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<PositionAnalysisResponse | null>(null)

  async function analyze() {
    const s = symbol.trim().toUpperCase()
    const bp = buyPrice.trim()
    if (!s || !bp) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const r = await apiFetchAnalyze(s, bp)
      setResult(r)
    } catch (e: any) {
      setError(e?.message || "วิเคราะห์ไม่สำเร็จ")
    } finally {
      setLoading(false)
    }
  }

  async function apiFetchAnalyze(sym: string, bp: string) {
    return apiFetchCompat<PositionAnalysisResponse>("/position/analyze/", {
      method: "POST",
      body: JSON.stringify({ symbol: sym, buy_price: bp }),
    })
  }

  async function apiFetchCompat<T>(path: string, options: RequestInit) {
    const url = ((import.meta as any).env.VITE_API_URL || "http://127.0.0.1:8000/api") + path
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) {
      throw new Error(data?.error || `API Error ${res.status}`)
    }
    return data as T
  }

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📌 วิเคราะห์สถานะถือหุ้น</div>
        <div className="page-subtitle">คำนวณ P/L และประเมินสัญญาณจากกฎ (ไม่ใช่คำแนะนำการลงทุน)</div>
      </div>

      <div className="page-body">
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="filters" style={{ gap: 10, flexWrap: "wrap" }}>
            <input
              className="filter-input"
              placeholder="Symbol เช่น PTT, AAPL"
              value={symbol}
              onChange={e => setSymbol(e.target.value.toUpperCase())}
              style={{ width: 180, fontFamily: "var(--font-mono)", fontWeight: 700 }}
            />
            <input
              className="filter-input"
              placeholder="ราคาเข้าซื้อ"
              value={buyPrice}
              onChange={e => setBuyPrice(e.target.value)}
              style={{ width: 160, fontFamily: "var(--font-mono)", fontWeight: 700 }}
              inputMode="decimal"
            />
            <button className="btn btn-primary" onClick={analyze} disabled={loading || !symbol.trim() || !buyPrice.trim()}>
              {loading ? "กำลังวิเคราะห์..." : "วิเคราะห์"}
            </button>
          </div>

          <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 10, lineHeight: 1.6 }}>
            ข้อควรทราบ: ผลลัพธ์นี้เป็น “การจัดระดับสัญญาณจากข้อมูลและกฎ” เพื่อช่วยทำความเข้าใจสถานะ ไม่ใช่คำแนะนำซื้อ/ขาย
          </div>
        </div>

        {error && (
          <div className="card" style={{ borderColor: "rgba(255,82,82,0.35)" }}>
            <div style={{ color: "var(--red)", fontWeight: 700 }}>เกิดข้อผิดพลาด</div>
            <div style={{ color: "var(--text-secondary)", marginTop: 6 }}>{error}</div>
          </div>
        )}

        {!error && !loading && !result && (
          <div className="empty-state" style={{ height: 320 }}>
            <span style={{ fontSize: 44 }}>📌</span>
            <span style={{ fontWeight: 600 }}>กรอก Symbol และราคาเข้าซื้อ แล้วกด “วิเคราะห์”</span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>ระบบจะดึงราคาตลาดล่าสุด + RSI/EMA/ADX จากฐานข้อมูล</span>
          </div>
        )}

        {result && (
          <div className="two-col" style={{ gap: 16 }}>
            <div className="card">
              <div className="card-title">สรุป</div>
              <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                <div style={{ fontFamily: "var(--font-mono)", fontSize: 22, fontWeight: 800, color: "var(--accent)" }}>
                  {result.symbol}
                </div>
                <span style={{
                  fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 800,
                  background: `${badgeColor(result.decision)}22`,
                  color: badgeColor(result.decision),
                  border: `1px solid ${badgeColor(result.decision)}44`,
                  borderRadius: 100, padding: "3px 10px",
                }}>
                  {decisionLabel(result.decision)}
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 14 }}>
                <div className="stat-card accent" style={{ padding: 14 }}>
                  <div className="stat-label">P/L (%)</div>
                  <div className="stat-value" style={{ fontSize: 22 }}>
                    {Number(result.pnl_pct).toFixed(2)}%
                  </div>
                </div>
                <div className="stat-card yellow" style={{ padding: 14 }}>
                  <div className="stat-label">คะแนนสัญญาณ</div>
                  <div className="stat-value" style={{ fontSize: 22 }}>
                    {Number(result.score).toFixed(0)}
                  </div>
                </div>
                <div className="stat-card green" style={{ padding: 14 }}>
                  <div className="stat-label">ความมั่นใจ</div>
                  <div className="stat-value" style={{ fontSize: 22 }}>
                    {Number(result.confidence).toFixed(0)}
                  </div>
                </div>
                <div className="stat-card" style={{ padding: 14 }}>
                  <div className="stat-label">ราคา</div>
                  <div style={{ marginTop: 6, fontFamily: "var(--font-mono)", fontWeight: 800 }}>
                    Buy: {Number(result.buy_price).toFixed(2)}<br />
                    Now: {Number(result.market_price).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-title">Indicators</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 10 }}>
                {[
                  ["RSI14", result.indicators.rsi14],
                  ["ADX14", result.indicators.adx14],
                  ["EMA20", result.indicators.ema20],
                  ["EMA50", result.indicators.ema50],
                  ["EMA200", result.indicators.ema200],
                ].map(([k, v]) => (
                  <div key={k as string} style={{
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "10px 12px",
                  }}>
                    <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", fontSize: 11, fontWeight: 800 }}>
                      {k as string}
                    </div>
                    <div style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)", fontSize: 14, fontWeight: 800, marginTop: 6 }}>
                      {v === null || v === undefined ? "—" : Number(v).toFixed(k === "RSI14" || k === "ADX14" ? 1 : 2)}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card" style={{ gridColumn: "1 / -1" }}>
              <div className="card-title">คำอธิบาย</div>
              <div style={{ whiteSpace: "pre-line", color: "var(--text-secondary)", lineHeight: 1.75 }}>
                {result.explanation}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

