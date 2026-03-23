import { useState, useRef } from "react"
import { api } from "../api/client"
import { TermText } from "../components/TermAssistant"
import SymbolInput from "../components/SymbolInput"

// ─── interfaces ──────────────────────────────────────────────────────────────

interface EquityCurvePoint {
  date: string;
  equity: number;
}

interface TradeLogItem {
  entry_date: string;
  entry_price: number;
  exit_date: string | null;
  exit_price: number | null;
  shares: number;
  pnl: number;
  pnl_pct: number;
  exit_reason: string;
  is_win: boolean;
}

interface BacktestResultData {
  symbol: string;
  start_date: string;
  end_date: string;
  total_return: number;
  total_return_thb: number;
  initial_capital: number;
  final_capital: number;
  win_rate: number;
  win_trades: number;
  loss_trades: number;
  total_trades: number;
  max_drawdown: number;
  sharpe_ratio: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  volatility: number;
  buy_hold_return: number;
  equity_curve: EquityCurvePoint[];
  trades: TradeLogItem[];
}

// ─── helpers ─────────────────────────────────────────────────────────────────
const fmt = (n: number | string, d = 2) => Number(n || 0).toLocaleString("th-TH", { minimumFractionDigits: d, maximumFractionDigits: d })
const fmtPct = (n: number | string) => `${Number(n || 0) >= 0 ? "+" : ""}${fmt(n)}%`
const fmtThb = (n: number | string) => `${Number(n || 0) >= 0 ? "+" : ""}฿${fmt(Math.abs(Number(n)), 0)}`

function StatCard({ label, value, sub, color, size = "md" }: { label: string, value: string, sub?: string, color?: string, size?: "md" | "lg" }) {
  return (
    <div style={{
      background: "var(--bg-surface)", border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)", padding: "14px 18px",
      borderTop: `2px solid ${color || "var(--border)"}`,
    }}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 600 }}>
        <TermText text={label} />
      </div>
      <div style={{
        fontFamily: "var(--font-mono)", fontWeight: 700, marginTop: 6,
        fontSize: size === "lg" ? 26 : 18,
        color: color || "var(--text-primary)",
      }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 3 }}><TermText text={sub} /></div>}
    </div>
  )
}

// ─── Equity Curve (SVG) ───────────────────────────────────────────────────────
function EquityCurve({ curve, initialCapital, mode }: { curve: EquityCurvePoint[], initialCapital: number, mode: string }) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [tooltip, setTooltip] = useState<{ idx: number, x: number, y: number } | null>(null)

  if (!curve || curve.length === 0) return (
    <div className="empty-state" style={{ height: 200 }}>ไม่มีข้อมูล Equity Curve</div>
  )

  const W = 700, H = 200, PAD = { top: 16, right: 20, bottom: 32, left: 70 }
  const iW = W - PAD.left - PAD.right
  const iH = H - PAD.top - PAD.bottom

  const values = curve.map(c => c.equity)
  const minV = Math.min(...values) * 0.995
  const maxV = Math.max(...values) * 1.005

  const xScale = (i: number) => PAD.left + (i / (curve.length - 1)) * iW
  const yScale = (v: number) => PAD.top + iH - ((v - minV) / (maxV - minV)) * iH

  // สร้าง path
  const points = curve.map((c, i) => `${xScale(i)},${yScale(c.equity)}`)
  const linePath = "M" + points.join("L")
  const areaPath = linePath + `L${xScale(curve.length - 1)},${PAD.top + iH} L${PAD.left},${PAD.top + iH}Z`

  const isProfit = values[values.length - 1] >= initialCapital
  const lineColor = isProfit ? "var(--green)" : "var(--red)"
  const areaColor = isProfit ? "rgba(0,230,118,0.12)" : "rgba(255,82,82,0.08)"

  // baseline (initial capital)
  const baseY = yScale(initialCapital)

  // Y axis ticks
  const yTicks = 4
  const yTickVals = Array.from({ length: yTicks + 1 }, (_, i) => minV + (maxV - minV) * i / yTicks)

  // X axis ticks (show ~5 dates)
  const xTickIdxs = [0, Math.floor(curve.length / 4), Math.floor(curve.length / 2), Math.floor(curve.length * 3 / 4), curve.length - 1]

  function handleMouseMove(e: React.MouseEvent) {
    if (!svgRef.current) return
    const rect = svgRef.current.getBoundingClientRect()
    const mx = (e.clientX - rect.left) * (W / rect.width) - PAD.left
    const idx = Math.round((mx / iW) * (curve.length - 1))
    if (idx >= 0 && idx < curve.length) {
      setTooltip({ idx, x: e.clientX - rect.left, y: e.clientY - rect.top })
    }
  }

  const modeLabel = mode === "signal" ? "Signal Mode" : "SL/TP Mode"
  const modeColor = mode === "signal" ? "var(--accent)" : "var(--yellow)"

  return (
    <div style={{ position: "relative" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>Equity Curve</span>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, color: modeColor,
          background: `${modeColor}22`, border: `1px solid ${modeColor}44`,
          borderRadius: 100, padding: "2px 8px"
        }}><TermText text={modeLabel} /></span>
      </div>
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "auto" }}
        onMouseMove={handleMouseMove} onMouseLeave={() => setTooltip(null)}>

        {/* Area */}
        <path d={areaPath} fill={areaColor} />
        {/* Line */}
        <path d={linePath} fill="none" stroke={lineColor} strokeWidth="1.5" />

        {/* Baseline */}
        {baseY >= PAD.top && baseY <= PAD.top + iH && (
          <line x1={PAD.left} y1={baseY} x2={PAD.left + iW} y2={baseY}
            stroke="var(--text-muted)" strokeWidth="0.5" strokeDasharray="3,3" />
        )}

        {/* Y axis ticks */}
        {yTickVals.map((v, i) => (
          <g key={i}>
            <line x1={PAD.left - 4} y1={yScale(v)} x2={PAD.left} y2={yScale(v)}
              stroke="var(--border)" strokeWidth="1" />
            <text x={PAD.left - 8} y={yScale(v) + 4} textAnchor="end"
              style={{ fontSize: 9, fill: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {(v / 1000).toFixed(0)}K
            </text>
          </g>
        ))}

        {/* X axis ticks */}
        {xTickIdxs.map(idx => idx < curve.length && (
          <text key={idx} x={xScale(idx)} y={H - 6} textAnchor="middle"
            style={{ fontSize: 8, fill: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {curve[idx].date.slice(5)}
          </text>
        ))}

        {/* Tooltip crosshair */}
        {tooltip && tooltip.idx < curve.length && (
          <g>
            <line x1={xScale(tooltip.idx)} y1={PAD.top}
              x2={xScale(tooltip.idx)} y2={PAD.top + iH}
              stroke="var(--accent)" strokeWidth="0.8" strokeDasharray="2,2" />
            <circle cx={xScale(tooltip.idx)} cy={yScale(curve[tooltip.idx].equity)}
              r="4" fill={lineColor} stroke="var(--bg-surface)" strokeWidth="1.5" />
          </g>
        )}
      </svg>

      {/* Tooltip box */}
      {tooltip && tooltip.idx < curve.length && (
        <div style={{
          position: "absolute", top: tooltip.y - 60, left: Math.min(tooltip.x + 10, 550),
          background: "var(--bg-elevated)", border: "1px solid var(--border)",
          borderRadius: 6, padding: "6px 10px", fontSize: 11, pointerEvents: "none",
          fontFamily: "var(--font-mono)", whiteSpace: "nowrap", zIndex: 10,
        }}>
          <div style={{ color: "var(--text-muted)" }}>{curve[tooltip.idx].date}</div>
          <div style={{ color: lineColor, fontWeight: 700, fontSize: 13 }}>
            ฿{fmt(curve[tooltip.idx].equity, 0)}
          </div>
          <div style={{ color: "var(--text-secondary)" }}>
            {fmtPct((curve[tooltip.idx].equity - initialCapital) / initialCapital * 100)}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Trade Log ────────────────────────────────────────────────────────────────
function TradeLog({ trades }: { trades: TradeLogItem[] }) {
  const [show, setShow] = useState(false)
  if (!trades || trades.length === 0)
    return <div style={{ color: "var(--text-muted)", fontSize: 13 }}>ไม่มี trade</div>

  const visible = show ? trades : trades.slice(-10).reverse()

  const REASON_LABELS: Record<string, { label: string, color: string }> = {
    SELL_SIGNAL: { label: "SELL Signal", color: "var(--red)" },
    STOP_LOSS: { label: "Stop Loss ❌", color: "var(--red)" },
    TAKE_PROFIT: { label: "Take Profit ✅", color: "var(--green)" },
    END: { label: "สิ้นสุด", color: "var(--text-muted)" },
  }

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>เข้า</th>
              <th style={{ textAlign: "right" }}>ราคาเข้า</th>
              <th>ออก</th>
              <th style={{ textAlign: "right" }}>ราคาออก</th>
              <th style={{ textAlign: "right" }}>กำไร/ขาดทุน</th>
              <th style={{ textAlign: "right" }}>%</th>
              <th>เหตุผล</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((t, i) => {
              const r = REASON_LABELS[t.exit_reason] || { label: t.exit_reason, color: "var(--text-muted)" }
              return (
                <tr key={i}>
                  <td style={{ fontFamily: "var(--font-mono)", color: "var(--text-muted)", fontSize: 11 }}>
                    {trades.length - i}
                  </td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{t.entry_date}</td>
                  <td style={{ fontFamily: "var(--font-mono)", textAlign: "right" }}>{fmt(t.entry_price)}</td>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>{t.exit_date || "-"}</td>
                  <td style={{ fontFamily: "var(--font-mono)", textAlign: "right" }}>{fmt(t.exit_price || 0)}</td>
                  <td style={{
                    fontFamily: "var(--font-mono)", fontWeight: 700, textAlign: "right",
                    color: t.is_win ? "var(--green)" : "var(--red)",
                  }}>{t.is_win ? "+" : ""}฿{fmt(t.pnl, 0)}</td>
                  <td style={{
                    fontFamily: "var(--font-mono)", textAlign: "right",
                    color: t.is_win ? "var(--green)" : "var(--red)",
                  }}>{fmtPct(t.pnl_pct)}</td>
                  <td>
                    <span style={{ fontSize: 11, color: r.color, fontWeight: 600 }}><TermText text={r.label} /></span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {trades.length > 10 && (
        <button className="btn btn-ghost" style={{ marginTop: 10, fontSize: 12 }}
          onClick={() => setShow(!show)}>
          {show ? "▲ ย่อ" : `▼ ดูทั้งหมด ${trades.length} trades`}
        </button>
      )}
    </div>
  )
}

// ─── Result Panel ─────────────────────────────────────────────────────────────
function ResultPanel({ result, mode }: { result: BacktestResultData, mode: string }) {
  const r = result
  const isProfit = r.total_return >= 0
  const retColor = isProfit ? "var(--green)" : "var(--red)"
  const [activeTab, setActiveTab] = useState("stats")

  return (
    <div style={{ marginTop: 24 }}>
      {/* Header */}
      <div style={{
        display: "flex", gap: 16, alignItems: "center",
        padding: "14px 20px",
        background: "var(--bg-surface)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg) var(--radius-lg) 0 0",
        borderBottom: "none",
      }}>
        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 16, color: "var(--accent)" }}>
          {r.symbol}
        </span>
        <span style={{ fontSize: 12, color: "var(--text-secondary)" }}>
          {r.start_date} → {r.end_date}
        </span>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 20, fontWeight: 700,
          color: retColor, marginLeft: "auto",
        }}>
          {fmtPct(r.total_return)}
          <span style={{ fontSize: 13, marginLeft: 8, color: "var(--text-secondary)" }}>
            ({fmtThb(r.total_return_thb)})
          </span>
        </span>
      </div>

      <div style={{
        background: "var(--bg-surface)", border: "1px solid var(--border)",
        borderRadius: "0 0 var(--radius-lg) var(--radius-lg)", padding: 20,
      }}>
        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, marginBottom: 20, borderBottom: "1px solid var(--border)", paddingBottom: 12 }}>
          {[["stats", "📊 สถิติ"], ["equity", "📈 Equity Curve"], ["trades", "📋 Trade Log"]].map(([id, label]) => (
            <button key={id} onClick={() => setActiveTab(id)} style={{
              padding: "6px 16px", borderRadius: 6, border: "none", cursor: "pointer",
              fontFamily: "var(--font-main)", fontSize: 13, fontWeight: 600,
              background: activeTab === id ? "var(--accent-dim)" : "transparent",
              color: activeTab === id ? "var(--accent)" : "var(--text-secondary)",
              borderBottom: activeTab === id ? "2px solid var(--accent)" : "2px solid transparent",
            }}>{label}</button>
          ))}
        </div>

        {/* Stats Tab */}
        {activeTab === "stats" && (
          <div>
            {/* Main stats grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
              <StatCard label="กำไรรวม" value={fmtPct(r.total_return)} color={retColor} size="lg" />
              <StatCard label="Win Rate" value={`${fmt(r.win_rate, 1)}%`} color="var(--green)"
                sub={`${r.win_trades}W / ${r.loss_trades}L จาก ${r.total_trades} trades`} />
              <StatCard label="Max Drawdown" value={`-${fmt(r.max_drawdown)}%`} color="var(--red)" />
              <StatCard label="Sharpe Ratio" value={fmt(r.sharpe_ratio)}
                color={r.sharpe_ratio >= 1 ? "var(--green)" : "var(--text-secondary)"} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
              <StatCard label="Profit Factor" value={fmt(r.profit_factor)}
                color={r.profit_factor >= 1.5 ? "var(--green)" : "var(--yellow)"} />
              <StatCard label="กำไรเฉลี่ย/trade" value={fmtPct(r.avg_win)} color="var(--green)" />
              <StatCard label="ขาดทุนเฉลี่ย/trade" value={fmtPct(r.avg_loss)} color="var(--red)" />
              <StatCard label="Volatility" value={`${fmt(r.volatility)}%`} color="var(--yellow)" />
            </div>

            {/* Comparison */}
            <div style={{
              background: "var(--bg-elevated)", borderRadius: "var(--radius)",
              padding: "14px 18px", display: "flex", gap: 32, alignItems: "center",
            }}>
              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                  Strategy Return
                </div>
                <div style={{
                  fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 20,
                  color: r.total_return >= 0 ? "var(--green)" : "var(--red)"
                }}>
                  {fmtPct(r.total_return)}
                </div>
              </div>
              <div style={{ fontSize: 20, color: "var(--text-muted)" }}>vs</div>
              <div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                  Buy & Hold
                </div>
                <div style={{
                  fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 20,
                  color: r.buy_hold_return >= 0 ? "var(--green)" : "var(--red)"
                }}>
                  {fmtPct(r.buy_hold_return)}
                </div>
              </div>
              <div style={{ marginLeft: "auto", textAlign: "right" }}>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>เงินทุนสุดท้าย</div>
                <div style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 16 }}>
                  ฿{fmt(r.final_capital, 0)}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  จาก ฿{fmt(r.initial_capital, 0)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Equity Curve Tab */}
        {activeTab === "equity" && (
          <EquityCurve curve={r.equity_curve} initialCapital={r.initial_capital} mode={mode} />
        )}

        {/* Trade Log Tab */}
        {activeTab === "trades" && <TradeLog trades={r.trades} />}
      </div>
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function Backtest() {
  const [symbol, setSymbol] = useState("")
  const [mode, setMode] = useState("both")
  const [start, setStart] = useState(() => {
    const d = new Date(); d.setFullYear(d.getFullYear() - 1)
    return d.toISOString().slice(0, 10)
  })
  const [end, setEnd] = useState(() => new Date().toISOString().slice(0, 10))
  const [capital, setCapital] = useState("100000")
  const [sl, setSl] = useState("5")
  const [tp, setTp] = useState("10")
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState("")

  async function handleRun() {
    if (!symbol.trim()) return setError("กรุณาใส่รหัสหุ้น")
    setError("")
    setLoading(true)
    setResults(null)
    try {
      const data = await api.runBacktest({
        symbol: symbol.toUpperCase(),
        mode, start, end,
        capital: parseFloat(capital),
        sl: parseFloat(sl),
        tp: parseFloat(tp),
      })
      if (data.error) throw new Error(data.error)
      setResults(data.results)
    } catch (e: any) {
      setError(e.message)
    }
    setLoading(false)
  }

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">⏪ Backtesting</div>
        <div className="page-subtitle">ทดสอบ Strategy ย้อนหลัง · วิเคราะห์ผลลัพธ์และสถิติ</div>
      </div>

      <div className="page-body">

        {/* ── Config Form ── */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title">⚙️ ตั้งค่า Backtest</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 }}>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                รหัสหุ้น *
              </label>
              <SymbolInput
                value={symbol} onChange={setSymbol} onSelect={handleRun}
                placeholder="เช่น PTT, KBANK, AAPL..."
                style={{ width: "100%" }} />
            </div>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                โหมด
              </label>
              <select className="filter-select" style={{ width: "100%" }} value={mode} onChange={e => setMode(e.target.value)}>
                <option value="both">ทั้งสองแบบ</option>
                <option value="signal">Signal Mode</option>
                <option value="sltp">SL/TP Mode</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                วันเริ่มต้น
              </label>
              <input type="date" className="filter-select" style={{ width: "100%" }}
                value={start} onChange={e => setStart(e.target.value)} />
            </div>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                วันสิ้นสุด
              </label>
              <input type="date" className="filter-select" style={{ width: "100%" }}
                value={end} onChange={e => setEnd(e.target.value)} />
            </div>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                เงินทุน (฿)
              </label>
              <input type="number" className="filter-input" style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                value={capital} onChange={e => setCapital(e.target.value)} />
            </div>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Stop Loss %
              </label>
              <input type="number" className="filter-input" style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                value={sl} onChange={e => setSl(e.target.value)} min="0.5" max="50" step="0.5" />
            </div>

            <div>
              <label style={{ fontSize: 11, color: "var(--text-muted)", display: "block", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                Take Profit %
              </label>
              <input type="number" className="filter-input" style={{ width: "100%", fontFamily: "var(--font-mono)" }}
                value={tp} onChange={e => setTp(e.target.value)} min="1" max="200" step="0.5" />
            </div>

            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button className="btn btn-primary" style={{ width: "100%", padding: "10px" }}
                onClick={handleRun} disabled={loading}>
                {loading ? "⏳ กำลังคำนวณ..." : "▶ รัน Backtest"}
              </button>
            </div>
          </div>

          {error && (
            <div style={{
              marginTop: 12, padding: "10px 14px", background: "var(--red-dim)",
              border: "1px solid rgba(255,82,82,0.3)", borderRadius: "var(--radius)",
              color: "var(--red)", fontSize: 13,
            }}>⚠️ {error}</div>
          )}
        </div>

        {/* ── Quick Symbols ── */}
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)", alignSelf: "center" }}>เลือกเร็ว:</span>
          {["PTT", "KBANK", "SCB", "ADVANC", "AAPL", "NVDA", "MSFT", "TSLA"].map(s => (
            <button key={s} onClick={() => setSymbol(s)} style={{
              padding: "4px 12px", borderRadius: 100, border: "1px solid var(--border)",
              background: symbol === s ? "var(--accent-dim)" : "transparent",
              color: symbol === s ? "var(--accent)" : "var(--text-secondary)",
              fontFamily: "var(--font-mono)", fontSize: 12, cursor: "pointer",
              transition: "all 0.15s",
            }}>{s}</button>
          ))}
        </div>

        {/* ── Loading ── */}
        {loading && (
          <div className="loading-state">
            <div className="loading-spinner" />
            <span>กำลังคำนวณ Backtest สำหรับ {symbol}...</span>
          </div>
        )}

        {/* ── Results ── */}
        {results && !loading && (
          <div>
            {results.signal && <ResultPanel result={results.signal} mode="signal" />}
            {results.sltp && <ResultPanel result={results.sltp} mode="sltp" />}
          </div>
        )}

        {/* ── Empty State ── */}
        {!results && !loading && (
          <div className="empty-state" style={{ padding: 60 }}>
            <span style={{ fontSize: 48 }}>⏪</span>
            <span style={{ fontSize: 15, fontWeight: 600 }}>เลือกหุ้นแล้วกด "รัน Backtest"</span>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>
              ระบบจะจำลองการซื้อขายย้อนหลังและแสดงสถิติครบถ้วน
            </span>
          </div>
        )}

      </div>
    </div>
  )
}
