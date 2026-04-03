import { useState, useCallback, useEffect, useRef } from "react"
import { api } from "../api/client"

// ── Types ─────────────────────────────────────────────────────────────────────
interface LayerResult {
  pass: boolean
  signal: string
  detail: string
  values?: Record<string, unknown>
  levels?: Array<{ type: string; price: number; strength: number; label?: string }>
  patterns?: Array<{ name: string; label: string }>
  pivots?: Record<string, number>
  nearest_support?: { price: number; strength: number } | null
  nearest_resistance?: { price: number; strength: number } | null
}

interface MLResult {
  symbol: string
  name: string
  exchange: string
  sector: string
  close: number
  layers_passed: number
  setup: string
  confidence: string
  direction: string
  layers: {
    trend: LayerResult
    structure: LayerResult
    pattern: LayerResult
    momentum: LayerResult
  }
}

interface MLResponse {
  count: number
  results: MLResult[]
}

// ── Constants ─────────────────────────────────────────────────────────────────
const SETUP_COLOR: Record<string, string> = {
  BUY:        "var(--green)",
  SELL:       "var(--red)",
  WATCH_BUY:  "var(--yellow)",
  WATCH_SELL: "#ff9800",
  NEUTRAL:    "var(--text-muted)",
}
const SETUP_LABEL: Record<string, string> = {
  BUY:        "คะแนนดี",
  SELL:       "คะแนนต่ำ",
  WATCH_BUY:  "เฝ้าดู",
  WATCH_SELL: "เฝ้าดู",
  NEUTRAL:    "เฝ้าดู",
}
const CONF_COLOR: Record<string, string> = {
  HIGH:   "var(--green)",
  MEDIUM: "var(--yellow)",
  LOW:    "#ff9800",
  NONE:   "var(--text-muted)",
}
const LAYER_LABEL = ["Trend", "Structure", "Pattern", "Momentum"]
const LAYER_ICON  = ["📈", "🏗️", "🕯️", "⚡"]
const LAYER_KEY   = ["trend", "structure", "pattern", "momentum"] as const

// ── Sub-components ────────────────────────────────────────────────────────────

function LayerDots({ result }: { result: MLResult }) {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      {LAYER_KEY.map((k, i) => {
        const layer = result.layers[k]
        return (
          <div
            key={k}
            title={`${LAYER_ICON[i]} ${LAYER_LABEL[i]}: ${layer.detail}`}
            style={{
              width: 10, height: 10, borderRadius: "50%",
              background: layer.pass ? "var(--green)" : "var(--bg-elevated)",
              border: `1.5px solid ${layer.pass ? "var(--green)" : "var(--border)"}`,
              flexShrink: 0,
              cursor: "help",
            }}
          />
        )
      })}
      <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 2 }}>
        {result.layers_passed}/4
      </span>
    </div>
  )
}

function LayerRow({ icon, label, layer, isLast }: {
  icon: string; label: string; layer: LayerResult; isLast?: boolean
}) {
  return (
    <div style={{
      display: "flex", gap: 12, alignItems: "flex-start",
      paddingBottom: isLast ? 0 : 12,
      borderBottom: isLast ? "none" : "1px solid var(--border)",
    }}>
      <div style={{
        width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "center",
        background: layer.pass ? "rgba(0,230,118,0.12)" : "var(--bg-elevated)",
        border: `1.5px solid ${layer.pass ? "var(--green)" : "var(--border)"}`,
        fontSize: 13,
      }}>{icon}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)" }}>{label}</span>
          <span style={{
            fontSize: 10, fontWeight: 700, padding: "2px 8px", borderRadius: 10,
            background: layer.pass ? "rgba(0,230,118,0.12)" : "var(--bg-elevated)",
            color: layer.pass ? "var(--green)" : "var(--text-muted)",
            border: `1px solid ${layer.pass ? "var(--green)33" : "var(--border)"}`,
          }}>
            {layer.pass ? "✓ ผ่าน" : "✗ ไม่ผ่าน"}
          </span>
        </div>
        <div style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5 }}>
          {layer.detail}
        </div>

        {/* แสดง S/R levels */}
        {layer.levels && layer.levels.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 6 }}>
            {layer.levels.slice(0, 6).map((lv, i) => (
              <span key={i} style={{
                fontSize: 9, fontWeight: 700, fontFamily: "var(--font-mono)",
                padding: "1px 6px", borderRadius: 4,
                background: lv.type === "S" ? "rgba(0,230,118,0.08)" : "rgba(255,70,70,0.08)",
                color: lv.type === "S" ? "var(--green)" : "var(--red)",
                border: `1px solid ${lv.type === "S" ? "var(--green)33" : "var(--red)33"}`,
              }}>
                {lv.label || lv.type}{lv.label ? "" : lv.strength > 1 ? `×${lv.strength}` : ""} {lv.price}
              </span>
            ))}
          </div>
        )}

        {/* แสดง candle patterns */}
        {layer.patterns && layer.patterns.length > 0 && (
          <div style={{ marginTop: 6 }}>
            {layer.patterns.map((p, i) => (
              <span key={i} style={{ fontSize: 10, color: "var(--yellow)", marginRight: 6 }}>
                {p.label}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function DetailPopup({ result, onClose, onAnalyze, onOpenChart }: {
  result: MLResult
  onClose: () => void
  onAnalyze?: (s: string) => void
  onOpenChart?: (s: string) => void
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener("mousedown", handler)
    return () => document.removeEventListener("mousedown", handler)
  }, [onClose])

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: 16,
    }}>
      <div ref={ref} style={{
        background: "var(--bg-card)", borderRadius: 12, border: "1px solid var(--border)",
        width: "100%", maxWidth: 520, maxHeight: "90vh", overflowY: "auto",
        padding: "24px", boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
      }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 20, fontWeight: 800, color: "var(--accent)" }}>{result.symbol}</span>
              <span style={{ fontSize: 10, background: "var(--bg-elevated)", padding: "2px 6px",
                borderRadius: 4, color: "var(--text-muted)", fontWeight: 700 }}>{result.exchange}</span>
              <span style={{
                fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 12,
                color: SETUP_COLOR[result.setup] || "var(--text-muted)",
                background: `${SETUP_COLOR[result.setup]}18` || "var(--bg-elevated)",
              }}>{SETUP_LABEL[result.setup] || result.setup}</span>
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>{result.name}</div>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", color: "var(--text-muted)",
            fontSize: 20, cursor: "pointer", padding: 4, lineHeight: 1,
          }}>✕</button>
        </div>

        {/* Confidence + Price */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <div style={{ flex: 1, padding: "10px 14px", background: "var(--bg-elevated)",
            borderRadius: 8, border: "1px solid var(--border)", textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>ผ่าน Layer</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: "var(--accent)" }}>
              {result.layers_passed}<span style={{ fontSize: 14, color: "var(--text-muted)" }}>/4</span>
            </div>
          </div>
          <div style={{ flex: 1, padding: "10px 14px", background: "var(--bg-elevated)",
            borderRadius: 8, border: "1px solid var(--border)", textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>ความน่าเชื่อถือ</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: CONF_COLOR[result.confidence] }}>
              {result.confidence}
            </div>
          </div>
          <div style={{ flex: 1, padding: "10px 14px", background: "var(--bg-elevated)",
            borderRadius: 8, border: "1px solid var(--border)", textAlign: "center" }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4 }}>ราคาปิด</div>
            <div style={{ fontSize: 16, fontWeight: 800, color: "var(--text-primary)" }}>
              {result.close?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
            </div>
          </div>
        </div>

        {/* Layer breakdown */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {LAYER_KEY.map((k, i) => (
            <LayerRow
              key={k}
              icon={LAYER_ICON[i]}
              label={LAYER_LABEL[i]}
              layer={result.layers[k]}
              isLast={i === 3}
            />
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 10, marginTop: 20, paddingTop: 16, borderTop: "1px solid var(--border)" }}>
          <button
            onClick={() => { onAnalyze?.(result.symbol); onClose() }}
            style={{
              flex: 1, padding: "10px 0", borderRadius: 8, fontSize: 13, fontWeight: 700,
              cursor: "pointer", border: "1px solid var(--accent)",
              background: "var(--accent-dim)", color: "var(--accent)",
            }}>🔬 วิเคราะห์</button>
          <button
            onClick={() => { onOpenChart?.(result.symbol); onClose() }}
            style={{
              flex: 1, padding: "10px 0", borderRadius: 8, fontSize: 13, fontWeight: 700,
              cursor: "pointer", border: "1px solid var(--border)",
              background: "transparent", color: "var(--text-secondary)",
            }}>📈 กราฟ</button>
        </div>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function MultiLayerScanner({ onOpenChart, onAnalyze }: {
  onOpenChart?: (s: string) => void
  onAnalyze?: (s: string) => void
}) {
  const [data, setData]       = useState<MLResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<MLResult | null>(null)

  // Filters
  const [exchange,  setExchange]  = useState("SET")
  const [minLayers, setMinLayers] = useState("3")
  const [setup,     setSetup]     = useState("")
  const [search,    setSearch]    = useState("")

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = { min_layers: minLayers }
      if (exchange) params.exchange = exchange
      if (setup)    params.setup    = setup
      const res = await (api as any).getMultiLayer(params)
      setData(res)
    } catch (e) {
      console.error("MultiLayer fetch error:", e)
    }
    setLoading(false)
  }, [exchange, minLayers, setup])

  useEffect(() => { load() }, [load])

  const filtered = (data?.results || []).filter(r => {
    if (search && !r.symbol.includes(search.toUpperCase()) && !r.name?.includes(search)) return false
    if (exchange === "US" && r.exchange !== "NASDAQ" && r.exchange !== "NYSE") return false
    if (exchange && exchange !== "US" && r.exchange !== exchange) return false
    return true
  })

  return (
    <div className="fade-up">
      <div className="page-header" style={{ padding: "24px 0 0" }}>
        <div className="page-title">🎯 Multi-Layer Scanner</div>
        <div className="page-subtitle">กรองหุ้นผ่านทั้ง 4 ด่าน — Trend · Structure · Pattern · Momentum</div>
      </div>

      <div className="page-body" style={{ padding: 0 }}>

        {/* ── Filter Bar ── */}
        <div className="card" style={{ marginBottom: 20 }}>

          {/* Strategy flow */}
          <div style={{
            display: "flex", gap: 0, marginBottom: 16,
            background: "var(--bg-elevated)", borderRadius: 10,
            border: "1px solid var(--border)", overflow: "hidden",
          }}>
            {[
              { icon: "📈", label: "Layer 1", sub: "Trend (EMA)" },
              { icon: "→", label: "", sub: "", arrow: true },
              { icon: "🏗️", label: "Layer 2", sub: "Structure (S/R)" },
              { icon: "→", label: "", sub: "", arrow: true },
              { icon: "🕯️", label: "Layer 3", sub: "Pattern (Candle)" },
              { icon: "→", label: "", sub: "", arrow: true },
              { icon: "⚡", label: "Layer 4", sub: "Momentum (RSI/MACD)" },
              { icon: "→", label: "", sub: "", arrow: true },
              { icon: "✅", label: "Setup", sub: "BUY / SELL" },
            ].map((s, i) =>
              s.arrow ? (
                <div key={i} style={{ display: "flex", alignItems: "center", color: "var(--text-muted)",
                  fontSize: 12, padding: "0 4px" }}>→</div>
              ) : (
                <div key={i} style={{ flex: 1, padding: "10px 8px", textAlign: "center" }}>
                  <div style={{ fontSize: 16, marginBottom: 2 }}>{s.icon}</div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--accent)" }}>{s.label}</div>
                  <div style={{ fontSize: 9, color: "var(--text-muted)" }}>{s.sub}</div>
                </div>
              )
            )}
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
            {/* Exchange */}
            <div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700,
                textTransform: "uppercase", marginBottom: 5 }}>ตลาด</div>
              <select className="filter-select" style={{ width: "100%" }}
                value={exchange} onChange={e => setExchange(e.target.value)}>
                <option value="">ทุกตลาด</option>
                <option value="SET">🇹🇭 SET</option>
                <option value="NASDAQ">🇺🇸 NASDAQ</option>
                <option value="NYSE">🇺🇸 NYSE</option>
              </select>
            </div>

            {/* Min Layers */}
            <div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700,
                textTransform: "uppercase", marginBottom: 5 }}>ผ่านอย่างน้อย</div>
              <div style={{ display: "flex", gap: 4 }}>
                {["2", "3", "4"].map(v => (
                  <button key={v} onClick={() => setMinLayers(v)}
                    style={{
                      flex: 1, padding: "6px 0", borderRadius: 6, fontSize: 12, fontWeight: 700,
                      cursor: "pointer",
                      border: `1px solid ${minLayers === v ? "var(--accent)" : "var(--border)"}`,
                      background: minLayers === v ? "var(--accent-dim)" : "transparent",
                      color: minLayers === v ? "var(--accent)" : "var(--text-secondary)",
                    }}>{v} Layer</button>
                ))}
              </div>
            </div>

            {/* Setup */}
            <div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700,
                textTransform: "uppercase", marginBottom: 5 }}>Setup</div>
              <select className="filter-select" style={{ width: "100%" }}
                value={setup} onChange={e => setSetup(e.target.value)}>
                <option value="">ทั้งหมด</option>
                <option value="BUY">คะแนนดี</option>
                <option value="SELL">คะแนนต่ำ</option>
                <option value="WATCH_BUY">เฝ้าดู</option>
                <option value="WATCH_SELL">เฝ้าดู (ขาลง)</option>
              </select>
            </div>

            {/* Search */}
            <div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700,
                textTransform: "uppercase", marginBottom: 5 }}>ค้นหา</div>
              <input className="filter-input" style={{ width: "100%" }}
                placeholder="ชื่อหุ้น / รหัส..."
                value={search} onChange={e => setSearch(e.target.value)} />
            </div>

            {/* Scan button */}
            <div style={{ display: "flex", alignItems: "flex-end" }}>
              <button className="btn btn-primary" style={{ width: "100%", height: 38 }}
                onClick={load} disabled={loading}>
                {loading ? "⏳ กำลังสแกน..." : "🎯 สแกน"}
              </button>
            </div>
          </div>
        </div>

        {/* ── Result Count ── */}
        {data && (
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "0 4px", marginBottom: 12 }}>
            <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
              พบ <b style={{ color: "var(--accent)", fontSize: 15 }}>{filtered.length}</b> หุ้น
              {setup && <span style={{ marginLeft: 6 }}>ที่เป็น {SETUP_LABEL[setup]}</span>}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
              กดที่แถวเพื่อดูรายละเอียด Layer
            </div>
          </div>
        )}

        {/* ── Loading / Empty ── */}
        {loading && (
          <div className="loading-state" style={{ height: 400 }}>
            <div className="loading-spinner" />
            <span>กำลังวิเคราะห์ทุก Layer...</span>
          </div>
        )}

        {!loading && data && filtered.length === 0 && (
          <div className="empty-state" style={{ height: 300 }}>
            <span style={{ fontSize: 40 }}>🎯</span>
            <span style={{ fontWeight: 600 }}>ไม่พบหุ้นที่ผ่านเงื่อนไข</span>
            <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
              ลองลด min layers หรือเปลี่ยนตลาด
            </span>
          </div>
        )}

        {/* ── Table ── */}
        {!loading && filtered.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ paddingLeft: 16 }}>หุ้น</th>
                  <th style={{ textAlign: "right" }}>ราคา</th>
                  <th style={{ textAlign: "center" }}>Setup</th>
                  <th style={{ textAlign: "center" }}>Layer ที่ผ่าน</th>
                  <th style={{ textAlign: "center" }}>📈 Trend</th>
                  <th style={{ textAlign: "center" }}>🏗️ Structure</th>
                  <th style={{ textAlign: "center" }}>🕯️ Pattern</th>
                  <th style={{ textAlign: "center" }}>⚡ Momentum</th>
                  <th style={{ textAlign: "center", paddingRight: 16 }}>ความมั่นใจ</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, i) => (
                  <tr key={i} onClick={() => setSelected(r)}
                    style={{ cursor: "pointer" }}
                    onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "var(--bg-elevated)"}
                    onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = ""}
                  >
                    <td style={{ paddingLeft: 16 }}>
                      <div className="symbol-cell">
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span className="symbol-code">{r.symbol}</span>
                          <span style={{ fontSize: 9, background: "var(--bg-elevated)", padding: "1px 4px",
                            borderRadius: 3, color: "var(--text-muted)", fontWeight: 700 }}>{r.exchange}</span>
                        </div>
                        <span className="symbol-name" style={{ fontSize: 11 }}>{r.name}</span>
                      </div>
                    </td>
                    <td style={{ textAlign: "right", fontFamily: "var(--font-mono)",
                      fontWeight: 700, fontSize: 13 }}>
                      {r.close?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <span style={{
                        fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 12,
                        color: SETUP_COLOR[r.setup] || "var(--text-muted)",
                        background: `${SETUP_COLOR[r.setup]}18` || "var(--bg-elevated)",
                      }}>{SETUP_LABEL[r.setup] || r.setup}</span>
                    </td>
                    <td style={{ textAlign: "center" }}>
                      <LayerDots result={r} />
                    </td>
                    {LAYER_KEY.map(k => (
                      <td key={k} style={{ textAlign: "center" }}>
                        <span style={{ fontSize: 14 }}>
                          {r.layers[k].pass ? "✅" : "❌"}
                        </span>
                      </td>
                    ))}
                    <td style={{ textAlign: "center", paddingRight: 16 }}>
                      <span style={{
                        fontSize: 11, fontWeight: 700,
                        color: CONF_COLOR[r.confidence] || "var(--text-muted)",
                      }}>{r.confidence}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Detail Popup ── */}
      {selected && (
        <DetailPopup
          result={selected}
          onClose={() => setSelected(null)}
          onAnalyze={onAnalyze}
          onOpenChart={onOpenChart}
        />
      )}
    </div>
  )
}
