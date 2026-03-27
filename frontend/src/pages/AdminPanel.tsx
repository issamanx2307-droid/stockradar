/**
 * AdminPanel.tsx — หน้าควบคุมระบบสำหรับ Superadmin
 */
import { useState, useEffect } from "react"
import { API_BASE } from "../api/config"
import { useAuth } from "../context/AuthContext"

interface SystemStats {
  total_users: number
  total_signals: number
  total_news: number
  total_symbols: number
  total_prices: number
  last_signal_date: string | null
}

export default function AdminPanel() {
  const { token } = useAuth()
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionMsg, setActionMsg] = useState("")
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_BASE}/admin/stats/`, {
      headers: { Authorization: `Token ${token}` },
    })
      .then(r => r.json())
      .then(d => { setStats(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  async function runAction(endpoint: string, label: string) {
    setActionLoading(label)
    setActionMsg("")
    try {
      const res = await fetch(`${API_BASE}/${endpoint}`, {
        method: "POST",
        headers: { Authorization: `Token ${token}`, "Content-Type": "application/json" },
      })
      const d = await res.json()
      setActionMsg(`✅ ${label}: ${d.message ?? d.status ?? "สำเร็จ"}`)
    } catch {
      setActionMsg(`❌ ${label}: ไม่สามารถเชื่อมต่อได้`)
    }
    setActionLoading(null)
  }

  const statCards = [
    { label: "สมาชิกทั้งหมด",   value: stats?.total_users    ?? "—", icon: "👥", color: "#00d4ff" },
    { label: "สัญญาณทั้งหมด",   value: stats?.total_signals  ?? "—", icon: "📡", color: "#00e676" },
    { label: "ข่าวทั้งหมด",     value: stats?.total_news     ?? "—", icon: "📰", color: "#ffd740" },
    { label: "หุ้นในระบบ",      value: stats?.total_symbols  ?? "—", icon: "📈", color: "#e040fb" },
    { label: "ราคาในฐานข้อมูล", value: stats?.total_prices?.toLocaleString() ?? "—", icon: "💾", color: "#ff6d00" },
  ]

  const actions = [
    { label: "รัน Engine (สร้างสัญญาณ)", endpoint: "trigger-engine/", icon: "⚙️", color: "#00e676" },
    { label: "ดึงข่าวล่าสุด",             endpoint: "admin/fetch-news/", icon: "📰", color: "#00d4ff" },
    { label: "Refresh Snapshot",          endpoint: "admin/refresh-snapshot/", icon: "🔄", color: "#ffd740" },
  ]

  return (
    <div style={{ padding: "24px 28px", maxWidth: 900, margin: "0 auto" }}>
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 24, fontWeight: 800, color: "#e2e8f0", margin: 0 }}>
          ⚙️ ควบคุมระบบ
        </h1>
        <p style={{ color: "#5a6e80", fontSize: 14, marginTop: 6 }}>
          Admin Panel — radarhoon.com
        </p>
      </div>

      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: 12, marginBottom: 32 }}>
        {statCards.map(c => (
          <div key={c.label} style={{
            padding: "18px 16px",
            background: "rgba(255,255,255,.03)",
            border: `1px solid ${c.color}22`,
            borderRadius: 12,
          }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>{c.icon}</div>
            <div style={{ fontSize: loading ? 14 : 22, fontWeight: 800, color: c.color, marginBottom: 4 }}>
              {loading ? "กำลังโหลด..." : c.value}
            </div>
            <div style={{ fontSize: 12, color: "#4a5a70" }}>{c.label}</div>
          </div>
        ))}
      </div>

      {/* System Actions */}
      <div style={{ marginBottom: 32 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: "#7a90a8", letterSpacing: 1, marginBottom: 16 }}>
          จัดการระบบ
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
          {actions.map(a => (
            <button key={a.label}
              disabled={actionLoading !== null}
              onClick={() => runAction(a.endpoint, a.label)}
              style={{
                padding: "12px 20px",
                background: actionLoading === a.label ? "rgba(255,255,255,.05)" : `${a.color}18`,
                border: `1px solid ${a.color}44`,
                borderRadius: 10, cursor: "pointer",
                color: a.color, fontWeight: 700, fontSize: 14,
                display: "flex", alignItems: "center", gap: 8,
                opacity: actionLoading !== null && actionLoading !== a.label ? 0.5 : 1,
                transition: "all .2s",
              }}
            >
              <span>{a.icon}</span>
              {actionLoading === a.label ? "⏳ กำลังรัน..." : a.label}
            </button>
          ))}
        </div>
        {actionMsg && (
          <div style={{
            marginTop: 14, padding: "10px 16px",
            background: actionMsg.startsWith("✅") ? "rgba(0,230,118,.08)" : "rgba(255,82,82,.08)",
            border: `1px solid ${actionMsg.startsWith("✅") ? "rgba(0,230,118,.25)" : "rgba(255,82,82,.25)"}`,
            borderRadius: 8, fontSize: 14,
            color: actionMsg.startsWith("✅") ? "#00e676" : "#ff5252",
          }}>
            {actionMsg}
          </div>
        )}
      </div>

      {/* Quick Links */}
      <div>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: "#7a90a8", letterSpacing: 1, marginBottom: 16 }}>
          ลิงก์ด่วน
        </h2>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
          {[
            { label: "Django Admin", url: "/admin/", icon: "🔑" },
            { label: "GitHub Actions", url: "https://github.com/issamanx2307-droid/stockradar/actions", icon: "🔁" },
            { label: "Hostinger VPS", url: "https://hpanel.hostinger.com", icon: "🖥️" },
          ].map(l => (
            <a key={l.label} href={l.url} target="_blank" rel="noopener noreferrer"
              style={{
                padding: "10px 18px",
                background: "rgba(255,255,255,.03)",
                border: "1px solid rgba(255,255,255,.1)",
                borderRadius: 8, textDecoration: "none",
                color: "#a0b4c8", fontSize: 14,
                display: "flex", alignItems: "center", gap: 8,
              }}>
              {l.icon} {l.label}
            </a>
          ))}
        </div>
      </div>

      {/* Last signal info */}
      {stats?.last_signal_date && (
        <div style={{ marginTop: 24, fontSize: 12, color: "#3a4a58" }}>
          สัญญาณล่าสุด: {new Date(stats.last_signal_date).toLocaleString("th-TH")}
        </div>
      )}
    </div>
  )
}
