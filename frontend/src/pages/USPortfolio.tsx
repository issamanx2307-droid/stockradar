/**
 * pages/USPortfolio.tsx
 * US Stock Portfolio ผ่าน Alpaca Paper Trading
 */
import { useState, useEffect, useCallback } from "react"
import { api } from "../api/client"

// ── helpers ────────────────────────────────────────────────────────────────
function fmt(n: number, decimals = 2) {
  return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}
function fmtMoney(n: number) {
  return `$${fmt(n)}`
}
function fmtPct(n: number) {
  const sign = n >= 0 ? "+" : ""
  return `${sign}${fmt(n)}%`
}
function colorPnl(n: number): string {
  return n >= 0 ? "var(--green, #4caf50)" : "var(--red, #f44336)"
}

// ── Mini P&L Chart (SVG) ────────────────────────────────────────────────────
function PnlChart({ history }: { history: { timestamp: number; equity: number }[] }) {
  if (!history || history.length < 2) {
    return (
      <div style={{ height: 120, display: "flex", alignItems: "center",
        justifyContent: "center", color: "var(--text-muted)", fontSize: 12 }}>
        ไม่มีข้อมูล
      </div>
    )
  }
  const W = 600, H = 120, PAD = 8
  const vals = history.map(h => h.equity)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1
  const pts = vals.map((v, i) => {
    const x = PAD + (i / (vals.length - 1)) * (W - PAD * 2)
    const y = PAD + (1 - (v - min) / range) * (H - PAD * 2)
    return `${x},${y}`
  })
  const color = vals[vals.length - 1] >= vals[0] ? "#4caf50" : "#f44336"
  const polyline = pts.join(" ")
  const areaBottom = `${W - PAD},${H - PAD} ${PAD},${H - PAD}`
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 120 }}>
      <defs>
        <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0.02" />
        </linearGradient>
      </defs>
      <polygon points={`${pts[0]} ${polyline} ${areaBottom}`} fill="url(#pnlGrad)" />
      <polyline points={polyline} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}

// ── Period selector ─────────────────────────────────────────────────────────
const PERIODS = [
  { label: "1D", value: "1D", tf: "5Min" },
  { label: "1W", value: "1W", tf: "1H" },
  { label: "1M", value: "1M", tf: "1D" },
  { label: "3M", value: "3M", tf: "1D" },
  { label: "1Y", value: "1A", tf: "1D" },
]

// ── Main Component ──────────────────────────────────────────────────────────
export default function USPortfolio() {
  const [account, setAccount]         = useState<any>(null)
  const [positions, setPositions]     = useState<any[]>([])
  const [orders, setOrders]           = useState<any[]>([])
  const [history, setHistory]         = useState<any[]>([])
  const [clock, setClock]             = useState<any>(null)
  const [period, setPeriod]           = useState("1M")
  const [loading, setLoading]         = useState(true)
  const [refreshing, setRefreshing]   = useState(false)
  const [error, setError]             = useState("")
  const [orderTab, setOrderTab]       = useState<"open" | "closed">("open")

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    setError("")
    try {
      const tf = PERIODS.find(p => p.value === period)?.tf ?? "1D"
      const [acc, pos, ord, hist, clk] = await Promise.all([
        api.alpacaAccount(),
        api.alpacaPositions(),
        api.alpacaOrders("all", 50),
        api.alpacaPortfolioHistory(period, tf),
        api.alpacaClock(),
      ])
      setAccount(acc)
      setPositions(pos)
      setOrders(ord)
      setHistory(hist?.history ?? [])
      setClock(clk)
    } catch (e: any) {
      setError(e.message || "ไม่สามารถโหลดข้อมูล Alpaca ได้")
    }
    setLoading(false)
    setRefreshing(false)
  }, [period])

  useEffect(() => { load() }, [load])

  // Auto-refresh ทุก 30 วิ
  useEffect(() => {
    const iv = setInterval(() => load(true), 30_000)
    return () => clearInterval(iv)
  }, [load])

  const filteredOrders = orders.filter(o =>
    orderTab === "open"
      ? ["new", "partially_filled", "pending_new", "accepted", "held"].includes(o.status)
      : ["filled", "cancelled", "expired", "rejected", "replaced"].includes(o.status)
  )

  const dayPnl = account ? parseFloat(account.equity) - parseFloat(account.last_equity ?? account.equity) : 0
  const dayPnlPct = account?.last_equity
    ? (dayPnl / parseFloat(account.last_equity)) * 100
    : 0

  if (loading) {
    return (
      <div className="fade-up" style={{ display: "flex", alignItems: "center",
        justifyContent: "center", minHeight: 300, flexDirection: "column", gap: 12 }}>
        <div className="loading-spinner" />
        <div style={{ color: "var(--text-muted)", fontSize: 13 }}>กำลังโหลดข้อมูล Alpaca...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="fade-up">
        <div className="page-header">
          <div className="page-title">🇺🇸 US Portfolio</div>
        </div>
        <div className="page-body">
          <div className="card" style={{ textAlign: "center", padding: 32 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>⚠️</div>
            <div style={{ color: "var(--text-muted)", fontSize: 14 }}>{error}</div>
            <button className="btn btn-primary" onClick={() => load()} style={{ marginTop: 16 }}>
              ลองใหม่
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fade-up">
      <div className="page-header">
        <div>
          <div className="page-title">🇺🇸 US Portfolio</div>
          <div className="page-subtitle">Alpaca Paper Trading — เงินจำลอง ไม่ใช่เงินจริง</div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Market Status */}
          {clock && (
            <div style={{
              padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 700,
              background: clock.is_open ? "rgba(76,175,80,0.15)" : "rgba(244,67,54,0.15)",
              color: clock.is_open ? "#4caf50" : "#f44336",
              border: `1px solid ${clock.is_open ? "#4caf50" : "#f44336"}44`,
            }}>
              {clock.is_open ? "🟢 ตลาดเปิด" : "🔴 ตลาดปิด"}
            </div>
          )}
          <button
            className="btn btn-secondary"
            onClick={() => load(true)}
            disabled={refreshing}
            style={{ fontSize: 12, padding: "4px 12px" }}
          >
            {refreshing ? "⟳" : "↻"} รีเฟรช
          </button>
        </div>
      </div>

      <div className="page-body">

        {/* ── Account Summary Cards ── */}
        {account && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
            <SummaryCard
              label="Portfolio Value"
              value={fmtMoney(parseFloat(account.portfolio_value ?? account.equity))}
              sub="มูลค่าพอร์ตรวม"
            />
            <SummaryCard
              label="Equity"
              value={fmtMoney(parseFloat(account.equity))}
              sub="ทุน + กำไรขาดทุน"
            />
            <SummaryCard
              label="Cash"
              value={fmtMoney(parseFloat(account.cash))}
              sub="เงินสดคงเหลือ"
            />
            <SummaryCard
              label="Buying Power"
              value={fmtMoney(parseFloat(account.buying_power))}
              sub="วงเงินซื้อขาย"
            />
            <SummaryCard
              label="Day P&L"
              value={fmtMoney(dayPnl)}
              sub={fmtPct(dayPnlPct)}
              valueColor={colorPnl(dayPnl)}
            />
          </div>
        )}

        {/* ── P&L Chart ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div className="card-title" style={{ margin: 0 }}>📈 Portfolio History</div>
            <div style={{ display: "flex", gap: 6 }}>
              {PERIODS.map(p => (
                <button key={p.value}
                  onClick={() => setPeriod(p.value)}
                  style={{
                    padding: "3px 10px", borderRadius: 6, fontSize: 12, border: "none",
                    cursor: "pointer", fontWeight: period === p.value ? 700 : 400,
                    background: period === p.value ? "var(--accent, #1976d2)" : "var(--bg-elevated)",
                    color: period === p.value ? "#fff" : "var(--text-muted)",
                  }}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <PnlChart history={history} />
          {history.length > 0 && (
            <div style={{ display: "flex", justifyContent: "space-between",
              fontSize: 11, color: "var(--text-muted)", marginTop: 4 }}>
              <span>{new Date(history[0].timestamp * 1000).toLocaleDateString("th-TH")}</span>
              <span>{new Date(history[history.length - 1].timestamp * 1000).toLocaleDateString("th-TH")}</span>
            </div>
          )}
        </div>

        {/* ── Positions ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title">📋 Positions ({positions.length})</div>
          {positions.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>
              ไม่มี position ที่เปิดอยู่
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: 11 }}>
                    <th style={thStyle}>Symbol</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Qty</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Avg Entry</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Current</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Mkt Value</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Unrealized P&L</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Today %</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map(pos => {
                    const pl = parseFloat(pos.unrealized_pl)
                    const plPct = parseFloat(pos.unrealized_plpc) * 100
                    const changeToday = parseFloat(pos.change_today) * 100
                    return (
                      <tr key={pos.symbol}
                        style={{ borderBottom: "1px solid var(--border)22" }}>
                        <td style={{ ...tdStyle, fontWeight: 700 }}>
                          <span style={{ color: pos.side === "long" ? "#4caf50" : "#f44336",
                            fontSize: 10, marginRight: 4 }}>
                            {pos.side === "long" ? "▲" : "▼"}
                          </span>
                          {pos.symbol}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                          {fmt(parseFloat(pos.qty), 0)}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                          {fmtMoney(parseFloat(pos.avg_entry_price))}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                          {fmtMoney(parseFloat(pos.current_price))}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                          {fmtMoney(parseFloat(pos.market_value))}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)",
                          color: colorPnl(pl) }}>
                          {fmtMoney(pl)}<br />
                          <span style={{ fontSize: 11 }}>{fmtPct(plPct)}</span>
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)",
                          color: colorPnl(changeToday) }}>
                          {fmtPct(changeToday)}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ── Order History ── */}
        <div className="card">
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
            <div className="card-title" style={{ margin: 0 }}>🗒️ Orders</div>
            <div style={{ display: "flex", gap: 6 }}>
              {(["open", "closed"] as const).map(tab => (
                <button key={tab}
                  onClick={() => setOrderTab(tab)}
                  style={{
                    padding: "3px 12px", borderRadius: 6, fontSize: 12, border: "none",
                    cursor: "pointer", fontWeight: orderTab === tab ? 700 : 400,
                    background: orderTab === tab ? "var(--accent, #1976d2)" : "var(--bg-elevated)",
                    color: orderTab === tab ? "#fff" : "var(--text-muted)",
                  }}
                >
                  {tab === "open" ? "เปิดอยู่" : "ปิดแล้ว"}
                </button>
              ))}
            </div>
          </div>

          {filteredOrders.length === 0 ? (
            <div style={{ color: "var(--text-muted)", fontSize: 13, textAlign: "center", padding: 20 }}>
              ไม่มี order
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--text-muted)", fontSize: 11 }}>
                    <th style={thStyle}>Symbol</th>
                    <th style={thStyle}>Side</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Qty</th>
                    <th style={{ ...thStyle, textAlign: "right" }}>Price</th>
                    <th style={thStyle}>Type</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>วันที่</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map(o => {
                    const isBuy = o.side === "buy"
                    const price = o.filled_avg_price
                      ? parseFloat(o.filled_avg_price)
                      : o.limit_price ? parseFloat(o.limit_price) : null
                    const dt = o.filled_at || o.submitted_at
                    return (
                      <tr key={o.id} style={{ borderBottom: "1px solid var(--border)22" }}>
                        <td style={{ ...tdStyle, fontWeight: 700 }}>{o.symbol}</td>
                        <td style={{ ...tdStyle, color: isBuy ? "#4caf50" : "#f44336", fontWeight: 700 }}>
                          {isBuy ? "BUY" : "SELL"}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                          {parseFloat(o.filled_qty) > 0
                            ? `${fmt(parseFloat(o.filled_qty), 0)}/${fmt(parseFloat(o.qty), 0)}`
                            : fmt(parseFloat(o.qty), 0)}
                        </td>
                        <td style={{ ...tdStyle, textAlign: "right", fontFamily: "var(--font-mono)" }}>
                          {price ? fmtMoney(price) : "market"}
                        </td>
                        <td style={{ ...tdStyle, color: "var(--text-muted)", fontSize: 11 }}>
                          {o.type}
                        </td>
                        <td style={tdStyle}>
                          <StatusBadge status={o.status} />
                        </td>
                        <td style={{ ...tdStyle, color: "var(--text-muted)", fontSize: 11 }}>
                          {dt ? new Date(dt).toLocaleString("th-TH", {
                            month: "short", day: "numeric",
                            hour: "2-digit", minute: "2-digit",
                          }) : "—"}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────
function SummaryCard({ label, value, sub, valueColor }: {
  label: string; value: string; sub: string; valueColor?: string
}) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
      <div style={{
        fontSize: 18, fontWeight: 800,
        fontFamily: "var(--font-mono)",
        color: valueColor ?? "var(--text-main)",
      }}>
        {value}
      </div>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>
    </div>
  )
}

const STATUS_COLORS: Record<string, string> = {
  filled:          "#4caf50",
  partially_filled: "#ff9800",
  new:             "#2196f3",
  pending_new:     "#2196f3",
  accepted:        "#2196f3",
  held:            "#9c27b0",
  cancelled:       "var(--text-muted)",
  expired:         "var(--text-muted)",
  rejected:        "#f44336",
  replaced:        "var(--text-muted)",
}
function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] ?? "var(--text-muted)"
  return (
    <span style={{
      padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 600,
      background: `${color}22`, color, border: `1px solid ${color}44`,
    }}>
      {status}
    </span>
  )
}

const thStyle: React.CSSProperties = {
  padding: "6px 8px", textAlign: "left", fontWeight: 600, whiteSpace: "nowrap",
}
const tdStyle: React.CSSProperties = {
  padding: "8px 8px", verticalAlign: "middle",
}
