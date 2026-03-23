import { useState, useEffect, useCallback } from "react"
import { api } from "../api/client"
import { ScannerResult } from "../api/types"
import { TermText } from "../components/TermAssistant"
import SymbolInput from "../components/SymbolInput"

const SIG_LABEL: Record<string, string> = {
  GOLDEN_CROSS: "Golden✕", EMA_ALIGNMENT: "EMA Align", EMA_PULLBACK: "EMA Pull",
  BREAKOUT: "Breakout", BUY: "ซื้อ", STRONG_BUY: "ซื้อแรง", OVERSOLD: "Oversold",
  DEATH_CROSS: "Death✕", BREAKDOWN: "Breakdown", SELL: "ขาย", STRONG_SELL: "ขายแรง",
  OVERBOUGHT: "Overbought", WATCH: "เฝ้าดู", ALERT: "แจ้งเตือน",
}
const DIR_COLOR: Record<string, string> = { LONG: "var(--green)", SHORT: "var(--red)", NEUTRAL: "var(--text-muted)" }
const DIR_LABEL: Record<string, string> = { LONG: "▲ LONG", SHORT: "▼ SHORT", NEUTRAL: "— " }

// ── Formulas ─────────────────────────────────────────────────────────────
const FORMULA_PRESETS = [
  { label: "🔍 ทุกหุ้น (แสดงทั้งหมด)", value: "" },
  { label: "📈 ราคาเหนือ EMA 200 (ขาขึ้น)", value: "close > ema(200)" },
  { label: "🔵 RSI Oversold (< 30)", value: "rsi(14) < 30" },
  { label: "🟡 RSI Overbought (> 70)", value: "rsi(14) > 70" },
  { label: "💥 Volume สูง (2x Avg)", value: "volume > volume_avg(20) * 2" },
  { label: "🚀 ราคาเบรค New High 20 วัน", value: "close > hh(20)" },
  { label: "📶 MACD ตัดขึ้น (Bullish)", value: "macd_hist > 0" },
  { label: "🛡️ ADX แข็งแกร่ง (> 25)", value: "adx14 > 25" },
]

function SignalBadge({ type, direction }: { type?: string; direction?: string }) {
  const cls = type?.toLowerCase()
  const dc = direction ? (DIR_COLOR[direction] || "var(--text-muted)") : "var(--text-muted)"
  return type ? (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <span className={`signal-badge ${cls}`}>{SIG_LABEL[type] || type}</span>
      {direction && direction !== "NEUTRAL" && (
        <span style={{
          fontSize: 10, fontWeight: 700, color: dc,
          fontFamily: "var(--font-mono)", letterSpacing: "0.05em"
        }}>
          {DIR_LABEL[direction]}
        </span>
      )}
    </div>
  ) : <span style={{ color: "var(--text-muted)", fontSize: 12 }}>—</span>
}

function RsiCell({ rsi }: { rsi?: number | null }) {
  if (rsi == null) return <span style={{ color: "var(--text-muted)" }}>—</span>
  const col = rsi < 30 ? "var(--blue)" : rsi > 70 ? "var(--yellow)" : "var(--text-secondary)"
  return <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: col }}>
    {rsi.toFixed(1)}
  </span>
}

function AdxCell({ adx, filterOk }: { adx?: number | null; filterOk?: boolean }) {
  if (adx == null) return <span style={{ color: "var(--text-muted)" }}>—</span>
  const col = adx > 25 ? "var(--green)" : "var(--text-muted)"
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: col }}>
      {adx.toFixed(1)}{filterOk ? " ✓" : ""}
    </span>
  )
}

function StopLossCell({ stopLoss, riskPct }: { close?: number; stopLoss?: number | null; riskPct?: number | null }) {
  if (!stopLoss) return <span style={{ color: "var(--text-muted)" }}>—</span>
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--red)", fontWeight: 600 }}>
        {stopLoss.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
      </span>
      {riskPct && (
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>
          Risk {riskPct.toFixed(1)}%
        </span>
      )}
    </div>
  )
}

function FilterBadges({ vol, atr, adx }: { vol?: boolean; atr?: boolean; adx?: boolean }) {
  return (
    <div style={{ display: "flex", gap: 3 }}>
      {( [["V", vol, "var(--accent)"], ["ATR", atr, "var(--yellow)"], ["ADX", adx, "var(--green)"]] as const ).map(([l, ok, c]) => (
        <span key={l} style={{
          fontSize: 9, fontWeight: 700, fontFamily: "var(--font-mono)",
          padding: "1px 4px", borderRadius: 3,
          background: ok ? `${c}22` : "var(--bg-elevated)",
          color: ok ? c : "var(--text-muted)",
          border: `1px solid ${ok ? c + "44" : "var(--border)"}`,
          opacity: ok ? 1 : 0.4,
        }}>{l}</span>
      ))}
    </div>
  )
}

export default function Scanner({ onOpenChart }: { onOpenChart: (s: string) => void }) {
  const [rows, setRows] = useState<ScannerResult[]>([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [total, setTotal] = useState(0)

  // Filters state
  const [exchange, setExchange] = useState("")
  const [signalType, setSignalType] = useState("")
  const [direction, setDirection] = useState("")
  const [minScore, setMinScore] = useState("")
  const [minAdx, setMinAdx] = useState("")
  const [minRsi, setMinRsi] = useState("")
  const [maxRsi, setMaxRsi] = useState("")
  const [search, setSearch] = useState("")
  const [onlyFiltered, setOnlyFiltered] = useState(false)
  
  const [strategyName, setStrategyName] = useState("")
  const [formula, setFormula] = useState("")
  const [customFormula, setCustomFormula] = useState(false)

  const buildParams = useCallback(() => {
    const p: Record<string, string> = {}
    if (exchange) p.exchange = exchange
    if (signalType) p.signal_type = signalType
    if (direction) p.direction = direction
    if (minScore) p.min_score = minScore
    if (minAdx) p.min_adx = minAdx
    if (minRsi) p.min_rsi = minRsi
    if (maxRsi) p.max_rsi = maxRsi
    if (strategyName) p.strategy_name = strategyName
    if (formula) p.formula = formula
    if (onlyFiltered) { p.filter_adx = "true"; p.filter_volume = "true" }
    return p
  }, [exchange, signalType, direction, minScore, minAdx, minRsi, maxRsi, strategyName, formula, onlyFiltered])

  const loadData = useCallback(() => {
    setLoading(true)
    const p = buildParams();
    console.log("🔍 Fetching scanner with params:", p);
    api.getScanner(p)
      .then(d => { 
        console.log("✅ Scanner data received:", d);
        setRows(d.results || []); 
        setTotal(d.count || 0);
      })
      .catch(e => {
        console.error("❌ Scanner fetch error:", e);
      })
      .finally(() => setLoading(false))
  }, [buildParams])

  useEffect(() => { loadData() }, [loadData])

  async function handleRun() {
    setRunning(true)
    try {
      await api.runScanner(exchange || "");
      loadData()
    } catch (e) {
      console.error(e)
    }
    setRunning(false)
  }

  const filtered = rows.filter(r =>
    !search || r.symbol.includes(search.toUpperCase()) || r.name?.includes(search)
  )

  return (
    <div className="fade-up scanner-container">
      <div className="page-header" style={{ padding: "24px 0 0" }}>
        <div className="page-title">🔍 สแกนหุ้นอัจฉริยะ</div>
        <div className="page-subtitle">ค้นหาหุ้นตามเงื่อนไขทางเทคนิคและกลยุทธ์เชิงปริมาณ</div>
      </div>

      <div className="page-body" style={{ padding: 0 }}>
        
        {/* ── Filter Section ── */}
        <div className="card" style={{ marginBottom: 24, border: '1px solid var(--border-light)' }}>
          <div className="filter-grid">
            
            {/* Group 1: Market & Strategy */}
            <div>
              <div className="filter-group-title"><span>🌍</span> ตลาดและกลยุทธ์</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <select className="filter-select" style={{ width: "100%" }} value={exchange} onChange={e => setExchange(e.target.value)}>
                  <option value="">ทุกตลาด</option>
                  <option value="SET">🇹🇭 ตลาดหุ้นไทย (SET)</option>
                  <option value="NASDAQ">🇺🇸 NASDAQ</option>
                  <option value="NYSE">🇺🇸 NYSE</option>
                </select>
                <select className="filter-select" style={{ width: "100%" }} value={strategyName} onChange={e => setStrategyName(e.target.value)}>
                  <option value="">เลือกกลยุทธ์สำเร็จรูป</option>
                  <option value="GOLDEN_CROSS">⭐ Golden Cross</option>
                  <option value="RSI_OVERSOLD">🔵 RSI Oversold</option>
                  <option value="BREAKOUT">🚀 Breakout</option>
                </select>
              </div>
            </div>

            {/* Group 2: Formula Selector */}
            <div>
              <div className="filter-group-title"><span>🧪</span> สูตรการสแกน</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {!customFormula ? (
                  <select className="filter-select" style={{ width: "100%", fontWeight: 600 }} 
                    value={formula} 
                    onChange={e => {
                      if (e.target.value === "CUSTOM") {
                        setCustomFormula(true);
                        setFormula("");
                      } else {
                        setFormula(e.target.value);
                      }
                    }}>
                    {FORMULA_PRESETS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
                    <option value="CUSTOM">➕ ใส่สูตรเอง (Advanced)...</option>
                  </select>
                ) : (
                  <div style={{ display: "flex", gap: 6 }}>
                    <input className="filter-input" style={{ flex: 1, fontFamily: 'var(--font-mono)' }} 
                      placeholder="เช่น close > ema(200)"
                      value={formula} onChange={e => setFormula(e.target.value)} />
                    <button className="btn btn-ghost" style={{ padding: '0 10px' }} onClick={() => { setCustomFormula(false); setFormula(""); }}>✕</button>
                  </div>
                )}
                <SymbolInput
                  value={search} onChange={setSearch}
                  placeholder="🔍 ค้นหาชื่อหุ้น หรือรหัส..."
                  style={{ width: "100%" }} />
              </div>
            </div>

            {/* Group 3: Technical Filters */}
            <div>
              <div className="filter-group-title"><span>📊</span> ตัวกรองเทคนิค</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <select className="filter-select" value={direction} onChange={e => setDirection(e.target.value)}>
                  <option value="">ทิศทาง</option>
                  <option value="LONG">▲ LONG</option>
                  <option value="SHORT">▼ SHORT</option>
                </select>
                <select className="filter-select" value={signalType} onChange={e => setSignalType(e.target.value)}>
                  <option value="">สัญญาณ</option>
                  <option value="BUY">🟢 BUY</option>
                  <option value="SELL">🔴 SELL</option>
                  <option value="BREAKOUT">🚀 Breakout</option>
                </select>
                <input className="filter-select" placeholder="ADX ≥" type="number"
                  value={minAdx} onChange={e => setMinAdx(e.target.value)} />
                <input className="filter-select" placeholder="RSI ≥" type="number"
                  value={minRsi} onChange={e => setMinRsi(e.target.value)} />
              </div>
            </div>

            {/* Group 4: Score & Actions */}
            <div>
              <div className="filter-group-title"><span>🎯</span> การประมวลผล</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", gap: 4 }}>
                  {["", "70", "80", "90"].map(v => (
                    <button key={v} onClick={() => setMinScore(v)} style={{
                      flex: 1, padding: "8px 0", borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: "pointer",
                      border: `1px solid ${minScore === v ? "var(--accent)" : "var(--border)"}`,
                      background: minScore === v ? "var(--accent-dim)" : "transparent",
                      color: minScore === v ? "var(--accent)" : "var(--text-secondary)",
                    }}>{v || "All"}</button>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn btn-primary" style={{ flex: 1.2, height: 38 }} onClick={loadData} disabled={loading}>
                    {loading ? "..." : "🔍 กรองหุ้น"}
                  </button>
                  <button className="btn btn-ghost" style={{ flex: 0.8, height: 38 }} onClick={handleRun} disabled={running}>
                    {running ? "⏳" : "▶ สแกน"}
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* ── Table Section ── */}
        <div className="scanner-table-container">
          <div className="scanner-header-actions">
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              พบหุ้น <b style={{ color: "var(--accent)", fontSize: 15 }}>{filtered.length}</b> ตัว จากทั้งหมด {total} ตัวในระบบ
            </div>
            <button onClick={() => setOnlyFiltered(!onlyFiltered)} style={{
              padding: "6px 16px", borderRadius: 20, fontSize: 11, fontWeight: 700, cursor: "pointer",
              border: `1px solid ${onlyFiltered ? "var(--green)" : "var(--border)"}`,
              background: onlyFiltered ? "var(--green-dim)" : "transparent",
              color: onlyFiltered ? "var(--green)" : "var(--text-secondary)",
              transition: "all 0.2s"
            }}>
              {onlyFiltered ? "✓ ผ่านตัวกรองพื้นฐานทั้งหมด" : "แสดงหุ้นทั้งหมด"}
            </button>
          </div>

          <div style={{ padding: 0 }}>
            {loading
              ? <div className="loading-state" style={{ height: 400 }}><div className="loading-spinner" /><span>กำลังประมวลผลข้อมูลมหาศาล...</span></div>
              : filtered.length === 0
                ? <div className="empty-state" style={{ height: 400 }}>
                    <span style={{ fontSize: 48 }}>🔍</span>
                    <span style={{ fontWeight: 600, fontSize: 16 }}>ไม่พบหุ้นที่ตรงตามเงื่อนไข</span>
                    <span style={{ fontSize: 13, color: "var(--text-muted)", maxWidth: 300, textAlign: 'center' }}>
                      ลองปรับลดความเข้มงวดของตัวกรอง หรือเปลี่ยนสูตรการสแกนใหม่
                    </span>
                  </div>
                : (
                  <div style={{ overflowX: "auto" }}>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th style={{ paddingLeft: 24 }}>หุ้น / ตลาด</th>
                          <th style={{ textAlign: "right" }}>ราคาปิด</th>
                          <th style={{ textAlign: "right" }}><TermText text="RSI (14)" /></th>
                          <th style={{ textAlign: "right" }}><TermText text="ADX (14)" /></th>
                          <th>สัญญาณเทรด</th>
                          <th style={{ textAlign: "right" }}>Stop Loss</th>
                          <th style={{ minWidth: 140 }}>ความแข็งแกร่ง (Score)</th>
                          <th style={{ paddingRight: 24 }}>ตัวกรอง</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.map((r, i) => (
                          <tr key={i} onClick={() => onOpenChart(r.symbol)} style={{ cursor: "pointer" }}>
                            <td style={{ paddingLeft: 24 }}>
                              <div className="symbol-cell">
                                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                  <span className="symbol-code">{r.symbol}</span>
                                  <span style={{ fontSize: 10, background: "var(--bg-elevated)", padding: "1px 4px", borderRadius: 3, color: "var(--text-muted)", fontWeight: 600 }}>{r.exchange}</span>
                                </div>
                                <span className="symbol-name" style={{ fontSize: 11 }}>{r.name}</span>
                              </div>
                            </td>
                            <td className="price-cell" style={{ textAlign: "right", fontWeight: 700, fontSize: 14 }}>
                              {r.close?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                            </td>
                            <td style={{ textAlign: "right" }}><RsiCell rsi={r.rsi} /></td>
                            <td style={{ textAlign: "right" }}>
                              {/* @ts-ignore */}
                              <AdxCell adx={r.adx14} filterOk={r.filter_adx} />
                            </td>
                            <td>
                              {/* @ts-ignore */}
                              <SignalBadge type={r.signal_type} direction={r.direction} />
                            </td>
                            <td style={{ textAlign: "right" }}>
                              {/* @ts-ignore */}
                              <StopLossCell close={r.close} stopLoss={r.stop_loss} riskPct={r.risk_pct} />
                            </td>
                            <td>
                              {r.score != null
                                ? <div className="score-bar">
                                  <div className="score-bar-track" style={{ height: 6 }}>
                                    <div className="score-bar-fill" style={{ width: `${r.score}%` }} />
                                  </div>
                                  <span className="score-text" style={{ fontSize: 13 }}>{r.score?.toFixed(0)}</span>
                                </div>
                                : <span style={{ color: "var(--text-muted)", fontSize: 12 }}>—</span>
                              }
                            </td>
                            <td style={{ paddingRight: 24 }}>
                              {/* @ts-ignore */}
                              <FilterBadges vol={r.filter_volume} atr={r.filter_volatility} adx={r.filter_adx} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )
            }
          </div>
        </div>
      </div>
    </div>
  )
}
