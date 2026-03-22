/**
 * pages/Portfolio.tsx
 * จัดการ Portfolio — เพิ่มหุ้น, ดู P/L, position sizing
 */
import { useState } from "react"
import { engineApi } from "../api/engineApi"
import DecisionBadge from "../components/DecisionBadge"

interface Position {
  symbol: string
  entry_price: number
  quantity: number
  stop_loss: number
  decision: string
  cost: number
}

interface Summary {
  capital: number
  cash: number
  invested: number
  market_value: number
  total_value: number
  unrealized_pnl: number
  return_pct: number
  positions: number
}

export default function Portfolio({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [capital, setCapital]       = useState(1000000)
  const [exchange, setExchange]     = useState("")
  const [minScore, setMinScore]     = useState(60)
  const [loading, setLoading]       = useState(false)
  const [summary, setSummary]       = useState<Summary | null>(null)
  const [decisions, setDecisions]   = useState<any[]>([])
  const [error, setError]           = useState("")

  async function handleRun() {
    setLoading(true); setError("")
    try {
      const res = await engineApi.portfolio({
        capital, exchange: exchange || undefined, min_score: minScore
      })
      setSummary(res.summary)
      setDecisions(res.decisions || [])
    } catch (e: any) {
      setError(e.message || "เกิดข้อผิดพลาด")
    }
    setLoading(false)
  }

  const isProfit = (summary?.return_pct ?? 0) >= 0

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">💼 Portfolio Allocation</div>
        <div className="page-subtitle">จัดสรรพอร์ตอัตโนมัติตาม 5-Factor Scoring Engine</div>
      </div>
      <div className="page-body">

        {/* ── Settings ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title">⚙️ ตั้งค่าพอร์ต</div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>เงินทุนทั้งหมด (บาท)</div>
              <input className="filter-input" type="number" value={capital}
                onChange={e => setCapital(Number(e.target.value))}
                style={{ width: 160, fontFamily: "var(--font-mono)", fontWeight: 700 }} />
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>ตลาด</div>
              <select className="filter-select" value={exchange}
                onChange={e => setExchange(e.target.value)}>
                <option value="">ทุกตลาด</option>
                <option value="SET">🇹🇭 SET</option>
                <option value="NYSE">🇺🇸 NYSE</option>
                <option value="NASDAQ">🇺🇸 NASDAQ</option>
              </select>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>Score ขั้นต่ำ</div>
              <div style={{ display: "flex", gap: 4 }}>
                {[40, 60, 80].map(s => (
                  <button key={s} onClick={() => setMinScore(s)} style={{
                    padding: "6px 12px", borderRadius: 6, fontSize: 12,
                    fontWeight: 600, cursor: "pointer",
                    border: `1px solid ${minScore === s ? "var(--accent)" : "var(--border)"}`,
                    background: minScore === s ? "var(--accent-dim)" : "transparent",
                    color: minScore === s ? "var(--accent)" : "var(--text-muted)",
                  }}>≥{s}</button>
                ))}
              </div>
            </div>
            <button className="btn btn-primary" onClick={handleRun}
              disabled={loading} style={{ height: 38, minWidth: 160 }}>
              {loading ? "⏳ กำลังวิเคราะห์..." : "🚀 สร้าง Portfolio"}
            </button>
          </div>
          {error && <div style={{ marginTop: 10, color: "var(--red)", fontSize: 13 }}>❌ {error}</div>}
        </div>

        {summary && (
          <>
            {/* ── Summary Cards ── */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
              {[
                { label: "เงินทุนทั้งหมด", val: `฿${summary.capital.toLocaleString()}`, color: "var(--accent)" },
                { label: "เงินสด",         val: `฿${summary.cash.toLocaleString()}`,    color: "var(--text-primary)" },
                { label: "มูลค่าพอร์ต",    val: `฿${summary.total_value.toLocaleString()}`, color: isProfit ? "var(--green)" : "var(--red)" },
                { label: "กำไร/ขาดทุน",    val: `${isProfit ? "+" : ""}${summary.return_pct.toFixed(2)}%`, color: isProfit ? "var(--green)" : "var(--red)" },
              ].map(({ label, val, color }) => (
                <div key={label} className="card" style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 6 }}>{label}</div>
                  <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color }}>{val}</div>
                </div>
              ))}
            </div>

            {/* ── Capital Allocation Bar ── */}
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title">📊 การจัดสรรเงินทุน</div>
              <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 12, color: "var(--green)", minWidth: 60 }}>
                  ลงทุน {((summary.invested / summary.capital) * 100).toFixed(1)}%
                </span>
                <div style={{ flex: 1, height: 12, background: "var(--border)", borderRadius: 6, overflow: "hidden" }}>
                  <div style={{
                    width: `${Math.min((summary.invested / summary.capital) * 100, 100)}%`,
                    height: "100%", background: "var(--accent)", borderRadius: 6, transition: "width 0.6s"
                  }} />
                </div>
                <span style={{ fontSize: 12, color: "var(--text-muted)", minWidth: 60, textAlign: "right" }}>
                  เงินสด {((summary.cash / summary.capital) * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                เปิด {summary.positions} positions · ลงทุน ฿{summary.invested.toLocaleString()} · เงินสดคงเหลือ ฿{summary.cash.toLocaleString()}
              </div>
            </div>

            {/* ── Positions Table ── */}
            {decisions.length > 0 && (
              <div className="card">
                <div className="card-title">📋 รายการ Positions ({decisions.length})</div>
                <div style={{ overflowX: "auto" }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>หุ้น</th>
                        <th>Decision</th>
                        <th style={{ textAlign: "right" }}>Score</th>
                        <th style={{ textAlign: "right" }}>Entry</th>
                        <th style={{ textAlign: "right" }}>Stop Loss</th>
                        <th style={{ textAlign: "right" }}>จำนวนหุ้น</th>
                        <th style={{ textAlign: "right" }}>ต้นทุน</th>
                      </tr>
                    </thead>
                    <tbody>
                      {decisions.map((d: any) => (
                        <tr key={d.symbol} onClick={() => onOpenChart?.(d.symbol)}
                          style={{ cursor: onOpenChart ? "pointer" : "default" }}>
                          <td>
                            <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--accent)" }}>
                              {d.symbol}
                            </span>
                          </td>
                          <td><DecisionBadge decision={d.decision} size="sm" /></td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontWeight: 700 }}>
                            {d.score}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)" }}>
                            {d.entry?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", color: "var(--red)" }}>
                            {d.stop_loss?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)" }}>
                            {d.size?.toLocaleString()}
                          </td>
                          <td style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontWeight: 600 }}>
                            ฿{d.cost?.toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {!summary && !loading && (
          <div className="empty-state">
            <span style={{ fontSize: 48 }}>💼</span>
            <span style={{ fontWeight: 600 }}>กำหนดเงินทุนแล้วกด "สร้าง Portfolio"</span>
            <span style={{ fontSize: 12, color: "var(--text-muted)", maxWidth: 320, textAlign: "center" }}>
              ระบบจะ scan ทุกหุ้น วิเคราะห์ด้วย 5-Factor Scoring แล้วจัดสรรเงินทุนให้อัตโนมัติ
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
