import { useState } from "react"
import { api } from "../api/client"
import { TermText } from "../components/TermAssistant"

// ─── Interfaces ──────────────────────────────────────────────────────────────

interface Condition {
  id: number;
  indicator: string;
  operator: string;
  target: string;
  value: string;
  logic: string;
}

interface Strategy {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  conditions: Condition[];
  signal: string;
}

interface RunResultData {
  strategy_name: string;
  total_scanned: number;
  matched_symbols: any[];
}

// ─── Preset Strategies ───────────────────────────────────────────────────────

const PRESET_STRATEGIES: Strategy[] = [
  {
    id: "ma_cross_bull",
    name: "MA Cross — Bullish",
    description: "EMA20 ข้าม EMA50 ขึ้น + ราคาเหนือ EMA200",
    icon: "⭐",
    color: "var(--green)",
    conditions: [
      { id: 1, indicator: "ema20", operator: "gt", target: "ema50", value: "", logic: "AND" },
      { id: 2, indicator: "ema50", operator: "gt", target: "ema200", value: "", logic: "AND" },
      { id: 3, indicator: "rsi", operator: "gt", target: "value", value: "45", logic: "AND" },
    ],
    signal: "BUY",
  },
  {
    id: "rsi_oversold",
    name: "RSI Oversold Bounce",
    description: "RSI ต่ำกว่า 30 + ราคาเหนือ EMA200",
    icon: "🔵",
    color: "var(--blue)",
    conditions: [
      { id: 1, indicator: "rsi", operator: "lt", target: "value", value: "30", logic: "AND" },
      { id: 2, indicator: "close", operator: "gt", target: "ema200", value: "", logic: "AND" },
    ],
    signal: "OVERSOLD",
  },
  {
    id: "macd_cross",
    name: "MACD Bullish Cross",
    description: "MACD Line ข้าม Signal Line ขึ้น",
    icon: "📶",
    color: "var(--accent)",
    conditions: [
      { id: 1, indicator: "macd", operator: "gt", target: "macd_signal", value: "", logic: "AND" },
      { id: 2, indicator: "macd_hist", operator: "gt", target: "value", value: "0", logic: "AND" },
    ],
    signal: "BUY",
  },
  {
    id: "bb_breakout",
    name: "Bollinger Breakout",
    description: "ราคาทะลุ BB Upper + Volume สูง",
    icon: "🚀",
    color: "var(--yellow)",
    conditions: [
      { id: 1, indicator: "close", operator: "gt", target: "bb_upper", value: "", logic: "AND" },
      { id: 2, indicator: "volume", operator: "gt", target: "vol_avg", value: "", logic: "AND" },
    ],
    signal: "BREAKOUT",
  },
  {
    id: "death_cross",
    name: "Death Cross — Bearish",
    description: "EMA20 ข้าม EMA50 ลง + RSI ต่ำกว่า 50",
    icon: "💀",
    color: "var(--red)",
    conditions: [
      { id: 1, indicator: "ema20", operator: "lt", target: "ema50", value: "", logic: "AND" },
      { id: 2, indicator: "ema50", operator: "lt", target: "ema200", value: "", logic: "AND" },
      { id: 3, indicator: "rsi", operator: "lt", target: "value", value: "50", logic: "AND" },
    ],
    signal: "SELL",
  },
  {
    id: "volume_spike",
    name: "Volume Spike",
    description: "ปริมาณซื้อขายสูงกว่าค่าเฉลี่ย 2 เท่า",
    icon: "💥",
    color: "var(--purple)",
    conditions: [
      { id: 1, indicator: "volume_ratio", operator: "gt", target: "value", value: "2", logic: "AND" },
      { id: 2, indicator: "rsi", operator: "gt", target: "value", value: "50", logic: "AND" },
    ],
    signal: "BREAKOUT",
  },
]

// ─── Indicator / Operator Options ────────────────────────────────────────────

const INDICATORS = [
  { value: "rsi", label: "RSI", unit: "", hasTarget: false },
  { value: "ema20", label: "EMA 20", unit: "฿", hasTarget: true },
  { value: "ema50", label: "EMA 50", unit: "฿", hasTarget: true },
  { value: "ema200", label: "EMA 200", unit: "฿", hasTarget: true },
  { value: "macd", label: "MACD Line", unit: "", hasTarget: true },
  { value: "macd_signal", label: "MACD Signal", unit: "", hasTarget: false },
  { value: "macd_hist", label: "MACD Histogram", unit: "", hasTarget: false },
  { value: "bb_upper", label: "BB Upper", unit: "฿", hasTarget: false },
  { value: "bb_lower", label: "BB Lower", unit: "฿", hasTarget: false },
  { value: "close", label: "ราคาปิด", unit: "฿", hasTarget: true },
  { value: "volume", label: "Volume", unit: "", hasTarget: true },
  { value: "volume_ratio", label: "Volume / ค่าเฉลี่ย 30วัน", unit: "x", hasTarget: false },
]

const OPERATORS = [
  { value: "gt", label: ">" },
  { value: "gte", label: "≥" },
  { value: "lt", label: "<" },
  { value: "lte", label: "≤" },
  { value: "eq", label: "=" },
  { value: "cross_up", label: "ข้ามขึ้น ↑" },
  { value: "cross_down", label: "ข้ามลง ↓" },
]

const TARGETS = [
  { value: "value", label: "ค่าที่กำหนด" },
  { value: "ema20", label: "EMA 20" },
  { value: "ema50", label: "EMA 50" },
  { value: "ema200", label: "EMA 200" },
  { value: "macd_signal", label: "MACD Signal" },
  { value: "bb_upper", label: "BB Upper" },
  { value: "bb_lower", label: "BB Lower" },
  { value: "vol_avg", label: "Volume เฉลี่ย 30วัน" },
]

const SIGNAL_TYPES = [
  { value: "BUY", label: "🟢 โมเมนตัมบวก", color: "var(--green)" },
  { value: "STRONG_BUY", label: "💚 โมเมนตัมบวกแรง", color: "var(--green)" },
  { value: "SELL", label: "🔴 โมเมนตัมลบ", color: "var(--red)" },
  { value: "STRONG_SELL", label: "❤️ โมเมนตัมลบแรง", color: "var(--red)" },
  { value: "BREAKOUT", label: "🚀 Breakout", color: "var(--yellow)" },
  { value: "OVERSOLD", label: "🔵 Oversold", color: "var(--blue)" },
  { value: "OVERBOUGHT", label: "🟡 Overbought", color: "var(--yellow)" },
  { value: "WATCH", label: "👁️ เฝ้าดู", color: "var(--accent)" },
]

// ─── Helpers ─────────────────────────────────────────────────────────────────

let nextId = 100
const newCondition = (): Condition => ({
  id: nextId++,
  indicator: "rsi",
  operator: "lt",
  target: "value",
  value: "30",
  logic: "AND",
})

function conditionToText(c: Condition) {
  const ind = INDICATORS.find(i => i.value === c.indicator)?.label || c.indicator
  const op = OPERATORS.find(o => o.value === c.operator)?.label || c.operator
  const tgt = c.target === "value"
    ? c.value
    : TARGETS.find(t => t.value === c.target)?.label || c.target
  return `${ind} ${op} ${tgt}`
}

// ─── Condition Row ────────────────────────────────────────────────────────────

function ConditionRow({ cond, index, onChange, onRemove }: { cond: Condition, index: number, total: number, onChange: (c: Condition) => void, onRemove: () => void }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "10px 14px",
      background: "var(--bg-elevated)",
      borderRadius: "var(--radius)",
      border: "1px solid var(--border)",
      animation: "fadeUp 0.2s ease",
    }}>
      {/* Logic badge */}
      {index > 0 && (
        <select
          value={cond.logic}
          onChange={e => onChange({ ...cond, logic: e.target.value })}
          style={{
            background: cond.logic === "AND" ? "var(--accent-dim)" : "var(--yellow-dim)",
            color: cond.logic === "AND" ? "var(--accent)" : "var(--yellow)",
            border: `1px solid ${cond.logic === "AND" ? "rgba(0,212,255,.3)" : "rgba(255,215,64,.3)"}`,
            borderRadius: 6, padding: "4px 8px",
            fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 11,
            cursor: "pointer", flexShrink: 0,
          }}>
          <option value="AND">AND</option>
          <option value="OR">OR</option>
        </select>
      )}
      {index === 0 && (
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
          color: "var(--text-muted)", padding: "4px 8px", flexShrink: 0,
        }}>IF</span>
      )}

      {/* Indicator */}
      <select className="filter-select" style={{ flex: 1, minWidth: 140 }}
        value={cond.indicator}
        onChange={e => onChange({ ...cond, indicator: e.target.value })}>
        {INDICATORS.map(i => <option key={i.value} value={i.value}>{i.label}</option>)}
      </select>

      {/* Operator */}
      <select className="filter-select" style={{ width: 100 }}
        value={cond.operator}
        onChange={e => onChange({ ...cond, operator: e.target.value })}>
        {OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>

      {/* Target */}
      <select className="filter-select" style={{ flex: 1, minWidth: 130 }}
        value={cond.target}
        onChange={e => onChange({ ...cond, target: e.target.value })}>
        {TARGETS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
      </select>

      {/* Value (only when target = value) */}
      {cond.target === "value" && (
        <input
          type="number"
          className="filter-select"
          style={{ width: 90, fontFamily: "var(--font-mono)" }}
          value={cond.value}
          onChange={e => onChange({ ...cond, value: e.target.value })}
          placeholder="ค่า"
        />
      )}

      {/* Remove */}
      <button onClick={onRemove} style={{
        background: "transparent", border: "none",
        color: "var(--text-muted)", cursor: "pointer", fontSize: 16,
        padding: "4px 6px", borderRadius: 4, flexShrink: 0,
        transition: "color 0.15s",
      }}
        onMouseEnter={e => (e.target as HTMLButtonElement).style.color = "var(--red)"}
        onMouseLeave={e => (e.target as HTMLButtonElement).style.color = "var(--text-muted)"}
      >✕</button>
    </div>
  )
}

// ─── Strategy Card (saved) ────────────────────────────────────────────────────

function StrategyCard({ strategy, onEdit, onDelete, onRun, running }: { strategy: Strategy, onEdit: (s: Strategy) => void, onDelete: (id: string) => void, onRun: (s: Strategy) => void, running: boolean }) {
  const sigColor = SIGNAL_TYPES.find(s => s.value === strategy.signal)?.color || "var(--accent)"
  return (
    <div style={{
      background: "var(--bg-surface)", border: "1px solid var(--border)",
      borderRadius: "var(--radius-lg)", padding: "16px 20px",
      transition: "border-color 0.2s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "var(--border-light)"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "var(--border)"}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: "var(--text-primary)" }}>
            {strategy.icon} {strategy.name}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>
            <TermText text={strategy.description} />
          </div>
        </div>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
          background: `${sigColor}22`, color: sigColor,
          border: `1px solid ${sigColor}44`,
          borderRadius: 100, padding: "3px 10px",
        }}>{strategy.signal}</span>
      </div>

      {/* Conditions preview */}
      <div style={{ marginBottom: 12 }}>
        {strategy.conditions.map((c, i) => (
          <div key={c.id} style={{
            display: "inline-flex", alignItems: "center", gap: 4,
            marginRight: 6, marginBottom: 4,
          }}>
            {i > 0 && (
              <span style={{
                fontSize: 10, fontFamily: "var(--font-mono)",
                color: c.logic === "AND" ? "var(--accent)" : "var(--yellow)",
                fontWeight: 700
              }}>{c.logic}</span>
            )}
            <span style={{
              background: "var(--bg-elevated)", border: "1px solid var(--border)",
              borderRadius: 4, padding: "2px 8px", fontSize: 11,
              fontFamily: "var(--font-mono)", color: "var(--text-secondary)",
            }}>{conditionToText(c)}</span>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: "flex", gap: 8 }}>
        <button className="btn btn-primary" style={{ fontSize: 12, padding: "6px 14px" }}
          onClick={() => onRun(strategy)} disabled={running}>
          {running ? "⏳" : "▶ รัน"}
        </button>
        <button className="btn btn-ghost" style={{ fontSize: 12, padding: "6px 14px" }}
          onClick={() => onEdit(strategy)}>✏️ แก้ไข</button>
        <button className="btn btn-ghost" style={{ fontSize: 12, padding: "6px 14px", marginLeft: "auto" }}
          onClick={() => onDelete(strategy.id)}>🗑</button>
      </div>
    </div>
  )
}

// ─── Run Result ───────────────────────────────────────────────────────────────

function RunResult({ result, onClose }: { result: RunResultData | null, onClose: () => void }) {
  if (!result) return null
  const signals = result.matched_symbols || []
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: 20,
    }} onClick={onClose}>
      <div style={{
        background: "var(--bg-surface)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-lg)", padding: 28, maxWidth: 560, width: "100%",
        maxHeight: "80vh", overflow: "auto",
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 16 }}>🔔 ผลการรัน Strategy</div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 3 }}>
              พบ {signals.length} หุ้น จาก {result.total_scanned} ตัว
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "transparent", border: "none", color: "var(--text-muted)",
            fontSize: 20, cursor: "pointer",
          }}>✕</button>
        </div>

        {signals.length === 0
          ? <div className="empty-state" style={{ padding: 40 }}>
            <span style={{ fontSize: 32 }}>🔍</span>
            <span>ไม่พบหุ้นที่ตรงเงื่อนไข</span>
          </div>
          : signals.map((s, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 12,
              padding: "10px 0", borderBottom: "1px solid var(--border)",
            }}>
              <span style={{
                fontFamily: "var(--font-mono)", fontWeight: 700,
                color: "var(--accent)", width: 72
              }}>{s.symbol}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, color: "var(--text-secondary)" }}>{s.name}</div>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 600 }}>
                {s.close?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
              </span>
              <span style={{
                fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700,
                background: "var(--green-dim)", color: "var(--green)",
                borderRadius: 100, padding: "2px 8px",
              }}>{s.score?.toFixed(0)}</span>
            </div>
          ))
        }
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function StrategyBuilder() {
  const [strategies, setStrategies] = useState<Strategy[]>(PRESET_STRATEGIES)
  const [editing, setEditing] = useState<Strategy | null>(null)       // strategy กำลังแก้ไข
  const [isNew, setIsNew] = useState(false)
  const [running, setRunning] = useState<string | null>(null)       // id ของ strategy กำลังรัน
  const [runResult, setRunResult] = useState<RunResultData | null>(null)
  const [activeTab, setActiveTab] = useState("list")     // list | editor

  // ── เริ่มสร้าง strategy ใหม่
  function handleNew() {
    setEditing({
      id: `custom_${Date.now()}`,
      name: "",
      description: "",
      icon: "🎯",
      color: "var(--accent)",
      conditions: [newCondition()],
      signal: "BUY",
    })
    setIsNew(true)
    setActiveTab("editor")
  }

  // ── โหลด preset มาแก้ไข
  function handleEdit(strategy: Strategy) {
    setEditing(JSON.parse(JSON.stringify(strategy)))
    setIsNew(false)
    setActiveTab("editor")
  }

  // ── บันทึก
  function handleSave() {
    if (!editing) return
    if (!editing.name.trim()) return alert("กรุณาใส่ชื่อ Strategy ครับ")
    if (editing.conditions.length === 0) return alert("กรุณาเพิ่มเงื่อนไขอย่างน้อย 1 ข้อครับ")

    if (isNew) {
      setStrategies(prev => [...prev, editing])
    } else {
      setStrategies(prev => prev.map(s => s.id === editing.id ? editing : s))
    }
    setActiveTab("list")
    setEditing(null)
  }

  // ── ลบ
  function handleDelete(id: string) {
    if (!confirm("ลบ Strategy นี้?")) return
    setStrategies(prev => prev.filter(s => s.id !== id))
  }

  // ── รัน Strategy — เรียก API Scanner
  async function handleRun(strategy: Strategy) {
    setRunning(strategy.id)
    try {
      const data = await api.getScanner({})
      // กรองหุ้นที่ตรงเงื่อนไข signal_type
      const matched = (data.results || [])
        .filter((r: any) => r.signal_type === strategy.signal)
        .slice(0, 20)

      setRunResult({
        strategy_name: strategy.name,
        total_scanned: (data as any).count || 0,
        matched_symbols: matched,
      })
    } catch (e: any) {
      alert("เรียก API ล้มเหลว: " + e.message)
    }
    setRunning(null)
  }

  // ── อัปเดต condition
  function updateCondition(id: number, updated: Condition) {
    if (!editing) return
    setEditing(prev => prev ? ({
      ...prev,
      conditions: prev.conditions.map(c => c.id === id ? updated : c),
    }) : null)
  }

  // ── เพิ่ม condition
  function addCondition() {
    if (!editing) return
    setEditing(prev => prev ? ({
      ...prev,
      conditions: [...prev.conditions, newCondition()],
    }) : null)
  }

  // ── ลบ condition
  function removeCondition(id: number) {
    if (!editing) return
    setEditing(prev => prev ? ({
      ...prev,
      conditions: prev.conditions.filter(c => c.id !== id),
    }) : null)
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="fade-up">
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div className="page-title">🎯 Strategy Builder</div>
            <div className="page-subtitle">สร้างและจัดการกลยุทธ์การเทรด · {strategies.length} strategies</div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {activeTab === "editor" && (
              <button className="btn btn-ghost" onClick={() => { setActiveTab("list"); setEditing(null) }}>
                ← กลับ
              </button>
            )}
            {activeTab === "list" && (
              <button className="btn btn-primary" onClick={handleNew}>
                + สร้าง Strategy ใหม่
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="page-body">

        {/* ══ LIST VIEW ══════════════════════════════════════════════════════ */}
        {activeTab === "list" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {strategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                strategy={strategy}
                onEdit={handleEdit}
                onDelete={handleDelete}
                onRun={handleRun}
                running={running === strategy.id}
              />
            ))}
          </div>
        )}

        {/* ══ EDITOR VIEW ════════════════════════════════════════════════════ */}
        {activeTab === "editor" && editing && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20, alignItems: "start" }}>

            {/* ── Left: Condition Builder ── */}
            <div>
              {/* Strategy Info */}
              <div className="card" style={{ marginBottom: 16 }}>
                <div className="card-title">ข้อมูล Strategy</div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  <div style={{ display: "flex", gap: 10 }}>
                    <input
                      className="filter-input"
                      style={{ width: 60, textAlign: "center", fontSize: 20 }}
                      value={editing.icon}
                      onChange={e => setEditing(p => p ? ({ ...p, icon: e.target.value }) : null)}
                      maxLength={2}
                    />
                    <input
                      className="filter-input"
                      style={{ flex: 1, fontWeight: 700 }}
                      placeholder="ชื่อ Strategy เช่น My MA Strategy"
                      value={editing.name}
                      onChange={e => setEditing(p => p ? ({ ...p, name: e.target.value }) : null)}
                    />
                  </div>
                  <input
                    className="filter-input"
                    style={{ width: "100%" }}
                    placeholder="คำอธิบาย (optional)"
                    value={editing.description}
                    onChange={e => setEditing(p => p ? ({ ...p, description: e.target.value }) : null)}
                  />
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ fontSize: 13, color: "var(--text-secondary)", flexShrink: 0 }}>
                      สัญญาณที่สร้าง:
                    </span>
                    <select className="filter-select" value={editing.signal}
                      onChange={e => setEditing(p => p ? ({ ...p, signal: e.target.value }) : null)}>
                      {SIGNAL_TYPES.map(s => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Conditions */}
              <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                  <div className="card-title" style={{ margin: 0 }}>
                    เงื่อนไข ({editing.conditions.length})
                  </div>
                  <button className="btn btn-ghost" style={{ fontSize: 12 }} onClick={addCondition}>
                    + เพิ่มเงื่อนไข
                  </button>
                </div>

                {editing.conditions.length === 0
                  ? <div className="empty-state" style={{ padding: 30 }}>
                    <span>กด "+ เพิ่มเงื่อนไข" เพื่อเริ่มสร้าง</span>
                  </div>
                  : <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {editing.conditions.map((cond, i) => (
                      <ConditionRow
                        key={cond.id}
                        cond={cond}
                        index={i}
                        total={editing.conditions.length}
                        onChange={updated => updateCondition(cond.id, updated)}
                        onRemove={() => removeCondition(cond.id)}
                      />
                    ))}
                  </div>
                }

                <div style={{ marginTop: 20, display: "flex", gap: 10 }}>
                  <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleSave}>
                    💾 บันทึก Strategy
                  </button>
                  <button className="btn btn-ghost" onClick={() => { setActiveTab("list"); setEditing(null) }}>
                    ยกเลิก
                  </button>
                </div>
              </div>
            </div>

            {/* ── Right: Preview ── */}
            <div style={{ position: "sticky", top: 20 }}>
              <div className="card">
                <div className="card-title">👁 Preview Strategy</div>

                <div style={{
                  background: "var(--bg-elevated)", borderRadius: "var(--radius)",
                  padding: 16, fontFamily: "var(--font-mono)", fontSize: 12,
                  color: "var(--text-secondary)", lineHeight: 1.8,
                }}>
                  {editing.conditions.length === 0
                    ? <span style={{ color: "var(--text-muted)" }}>ยังไม่มีเงื่อนไข...</span>
                    : editing.conditions.map((c, i) => (
                      <div key={c.id}>
                        {i === 0
                          ? <span style={{ color: "var(--accent)" }}>IF </span>
                          : <span style={{ color: c.logic === "AND" ? "var(--accent)" : "var(--yellow)" }}>
                            {c.logic}{" "}
                          </span>
                        }
                        <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>
                          {conditionToText(c)}
                        </span>
                      </div>
                    ))
                  }
                  {editing.conditions.length > 0 && (
                    <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border)" }}>
                      <span style={{ color: "var(--yellow)" }}>→ SIGNAL </span>
                      <span style={{ color: "var(--green)", fontWeight: 700 }}>{editing.signal}</span>
                    </div>
                  )}
                </div>

                {/* Quick presets */}
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    โหลด Preset
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {PRESET_STRATEGIES.map(p => (
                      <button key={p.id} className="btn btn-ghost"
                        style={{ fontSize: 11, textAlign: "left", padding: "6px 10px" }}
                        onClick={() => setEditing(prev => prev ? ({
                          ...prev,
                          conditions: JSON.parse(JSON.stringify(p.conditions)),
                          signal: p.signal,
                        }) : null)}>
                        {p.icon} {p.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* ── Run Result Modal ── */}
      <RunResult result={runResult} onClose={() => setRunResult(null)} />
    </div>
  )
}
