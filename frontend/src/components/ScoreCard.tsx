/**
 * components/ScoreCard.tsx
 * Card แสดง score breakdown แบบ visual bar
 */
import DecisionBadge from "./DecisionBadge"
import type { EngineResult } from "../api/engineApi"

interface Props {
  data: EngineResult
  onClick?: () => void
}

const BREAKDOWN_CONFIG = [
  { key: "trend",       label: "Trend",      max: 40, color: "#00d4ff" },
  { key: "momentum",    label: "Momentum",   max: 25, color: "#ffd740" },
  { key: "volume",      label: "Volume",     max: 15, color: "#69f0ae" },
  { key: "volatility",  label: "Volatility", max: 10, color: "#ce93d8" },
]

export default function ScoreCard({ data, onClick }: Props) {
  const score = typeof data.score === "number" ? data.score : (data as any).score?.total_score ?? 0
  const bd = (data as any).breakdown || {}
  // normalize decision: "STRONG_BUY" → "STRONG BUY"
  const decision = (data.decision || "").replace(/_/g, " ") as any

  return (
    <div onClick={onClick} style={{
      background: "var(--bg-surface, #1a2332)",
      border: "1px solid var(--border)",
      borderRadius: 12, padding: 16, cursor: onClick ? "pointer" : "default",
      transition: "transform 0.15s, border-color 0.15s",
    }}
      onMouseEnter={e => { if (onClick) { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.borderColor = "var(--accent)" }}}
      onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.borderColor = "var(--border)" }}
    >
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 16 }}>{data.symbol}</span>
        <DecisionBadge decision={decision} size="sm" />
      </div>

      {/* Score Ring */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
        <div style={{ position: "relative", width: 52, height: 52, flexShrink: 0 }}>
          <svg width="52" height="52" viewBox="0 0 52 52">
            <circle cx="26" cy="26" r="22" fill="none" stroke="var(--border)" strokeWidth="4"/>
            <circle cx="26" cy="26" r="22" fill="none"
              stroke={score >= 80 ? "#00c853" : score >= 60 ? "#00e676" : score >= 40 ? "#ffd600" : "#ff5252"}
              strokeWidth="4" strokeLinecap="round"
              strokeDasharray={`${(score / 100) * 138} 138`}
              transform="rotate(-90 26 26)"
            />
          </svg>
          <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center",
            justifyContent: "center", fontWeight: 700, fontSize: 13 }}>{score}</span>
        </div>
        <div style={{ flex: 1, fontSize: 12, color: "var(--text-muted)", lineHeight: 1.6 }}>
          <div>Entry: <b style={{ color: "var(--text-primary)", fontFamily: "var(--font-mono)" }}>
            {data.entry?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
          </b></div>
          <div>Stop: <b style={{ color: "var(--red)", fontFamily: "var(--font-mono)" }}>
            {data.stop_loss?.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
          </b> <span style={{ color: "var(--text-muted)" }}>({data.risk_pct}%)</span></div>
          {data.rsi && <div>RSI: <b style={{ fontFamily: "var(--font-mono)" }}>{data.rsi.toFixed(1)}</b></div>}
        </div>
      </div>

      {/* Score Breakdown Bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {BREAKDOWN_CONFIG.map(({ key, label, max, color }) => {
          const val = bd[key] ?? 0
          const pct = (val / max) * 100
          return (
            <div key={key}>
              <div style={{ display: "flex", justifyContent: "space-between",
                fontSize: 10, color: "var(--text-muted)", marginBottom: 2 }}>
                <span>{label}</span><span>{val}/{max}</span>
              </div>
              <div style={{ height: 4, background: "var(--border)", borderRadius: 2 }}>
                <div style={{ width: `${pct}%`, height: "100%",
                  background: color, borderRadius: 2, transition: "width 0.5s" }} />
              </div>
            </div>
          )
        })}
        {bd.risk_penalty > 0 && (
          <div style={{ fontSize: 10, color: "var(--red)", marginTop: 2 }}>
            ⚠️ Risk Penalty: −{bd.risk_penalty}
          </div>
        )}
      </div>
    </div>
  )
}
