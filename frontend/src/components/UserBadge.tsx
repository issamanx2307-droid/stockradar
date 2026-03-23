/**
 * components/UserBadge.tsx
 * แสดงข้อมูล user + tier badge + logout ใน Sidebar
 */
import { useAuth } from "../context/AuthContext"

const TIER_CONFIG: Record<string, { icon: string; color: string; label: string }> = {
  free:    { icon: "🆓", color: "#78909c", label: "Free"    },
  pro:     { icon: "⭐", color: "#00d4ff", label: "Pro"     },
  premium: { icon: "💎", color: "#ffd600", label: "Premium" },
}

export default function UserBadge({ onSubscription }: { onSubscription?: () => void }) {
  const { user, logout } = useAuth()
  if (!user) return null

  const tier = TIER_CONFIG[user.tier] || TIER_CONFIG.free

  return (
    <div style={{
      padding: "10px 12px", borderRadius: 10, marginBottom: 8,
      background: "var(--bg-elevated)", border: "1px solid var(--border)",
    }}>
      {/* Avatar + Name */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        {user.picture ? (
          <img src={user.picture} alt="" style={{ width: 28, height: 28,
            borderRadius: "50%", border: "2px solid var(--border)" }} />
        ) : (
          <div style={{ width: 28, height: 28, borderRadius: "50%",
            background: "var(--accent-dim)", display: "flex", alignItems: "center",
            justifyContent: "center", fontSize: 12, fontWeight: 700, color: "var(--accent)" }}>
            {(user.first_name || user.email)[0]?.toUpperCase()}
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-primary)",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {user.first_name || user.username}
          </div>
          <div style={{ fontSize: 10, color: "var(--text-muted)",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {user.email}
          </div>
        </div>
      </div>
      {/* Tier badge */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <span style={{
          fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 10,
          background: `${tier.color}18`, color: tier.color,
          border: `1px solid ${tier.color}44`,
        }}>{tier.icon} {tier.label}</span>
        {user.tier === "free" && (
          <button onClick={onSubscription} style={{
            fontSize: 9, padding: "2px 6px", borderRadius: 6,
            background: "rgba(0,212,255,.12)", color: "var(--accent)",
            border: "1px solid rgba(0,212,255,.3)", cursor: "pointer", fontWeight: 700,
          }}>อัปเกรด ↑</button>
        )}
      </div>
      {/* Logout */}
      <button onClick={logout} style={{
        width: "100%", padding: "5px 0", borderRadius: 6, fontSize: 11,
        background: "transparent", border: "1px solid var(--border)",
        color: "var(--text-muted)", cursor: "pointer", fontWeight: 600,
        transition: "all .15s",
      }}
        onMouseEnter={e => { (e.currentTarget as any).style.borderColor = "var(--red)"; (e.currentTarget as any).style.color = "var(--red)" }}
        onMouseLeave={e => { (e.currentTarget as any).style.borderColor = "var(--border)"; (e.currentTarget as any).style.color = "var(--text-muted)" }}
      >ออกจากระบบ</button>
    </div>
  )
}
