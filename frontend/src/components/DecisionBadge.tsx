/**
 * components/DecisionBadge.tsx
 * Badge แสดง STRONG BUY / BUY / HOLD / WATCH / SELL
 */
interface Props { decision: string; size?: "sm" | "md" }

const CONFIG: Record<string, { label: string; bg: string; color: string }> = {
  "STRONG BUY": { label: "💚 STRONG BUY", bg: "rgba(0,200,83,0.18)",  color: "#00c853" },
  "BUY":        { label: "🟢 BUY",        bg: "rgba(0,230,118,0.12)", color: "#00e676" },
  "HOLD":       { label: "🟡 HOLD",       bg: "rgba(255,214,0,0.12)", color: "#ffd600" },
  "WATCH":      { label: "🔵 WATCH",      bg: "rgba(41,182,246,0.12)",color: "#29b6f6" },
  "SELL":       { label: "🔴 SELL",       bg: "rgba(255,82,82,0.12)", color: "#ff5252" },
}

export default function DecisionBadge({ decision, size = "md" }: Props) {
  const cfg = CONFIG[decision] || { label: decision, bg: "var(--bg-elevated)", color: "var(--text-muted)" }
  return (
    <span style={{
      background: cfg.bg, color: cfg.color,
      border: `1px solid ${cfg.color}44`,
      borderRadius: 6,
      padding: size === "sm" ? "2px 8px" : "4px 12px",
      fontSize: size === "sm" ? 11 : 13,
      fontWeight: 700, whiteSpace: "nowrap",
    }}>
      {cfg.label}
    </span>
  )
}
