import { useState, useEffect } from "react"
import { api } from "../api/client"
import { useAuth } from "../context/AuthContext"

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  FREE:    { label: "FREE",    color: "var(--text-muted)", bg: "var(--bg-elevated)", icon: "◻" },
  PRO:     { label: "PRO",     color: "#f59e0b",           bg: "rgba(245,158,11,0.12)", icon: "★" },
  PREMIUM: { label: "PREMIUM", color: "var(--accent)",     bg: "var(--accent-dim)",   icon: "◈" },
}

export default function Profile() {
  const { user: authUser, logout } = useAuth()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [profileData, setProfileData] = useState<any>(null)
  const [lineToken, setLineToken] = useState("")
  const [telegramId, setTelegramId] = useState("")

  useEffect(() => { loadProfile() }, [])

  async function loadProfile() {
    try {
      const data = await api.getProfile()
      setProfileData(data)
      setLineToken(data.profile?.line_notify_token || "")
      setTelegramId(data.profile?.telegram_chat_id || "")
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    setSaving(true)
    setSaveMsg(null)
    try {
      await api.updateProfile({ line_notify_token: lineToken, telegram_chat_id: telegramId })
      setSaveMsg({ ok: true, text: "บันทึกการตั้งค่าสำเร็จ" })
    } catch {
      setSaveMsg({ ok: false, text: "เกิดข้อผิดพลาดในการบันทึก" })
    } finally {
      setSaving(false)
      setTimeout(() => setSaveMsg(null), 3000)
    }
  }

  function handleLogout() {
    if (confirm("ยืนยันการออกจากระบบ?")) logout()
  }

  if (loading) return (
    <div className="loading-state">
      <div className="loading-spinner" />
      <span>กำลังโหลดโปรไฟล์...</span>
    </div>
  )

  const tier = (profileData?.profile?.tier || authUser?.tier || "FREE").toUpperCase()
  const tc = TIER_CONFIG[tier] || TIER_CONFIG.FREE
  const displayName = authUser?.first_name || authUser?.username || profileData?.username || "ผู้ใช้"
  const email = authUser?.email || profileData?.email || ""
  const avatarLetter = displayName.charAt(0).toUpperCase()
  const picture = authUser?.picture

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">⚙️ โปรไฟล์ / ตั้งค่า</div>
        <div className="page-subtitle">จัดการบัญชี · การแจ้งเตือน · ข้อมูลสมาชิก</div>
      </div>
      <div className="page-body">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>

          {/* ── User Info Card ── */}
          <div className="card" style={{ gridColumn: "1 / -1" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
              {/* Avatar */}
              <div style={{ width: 64, height: 64, borderRadius: "50%", overflow: "hidden",
                background: "var(--accent-dim)", border: "2px solid var(--accent)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 26, fontWeight: 800, color: "var(--accent)", flexShrink: 0 }}>
                {picture
                  ? <img src={picture} alt={displayName} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  : avatarLetter}
              </div>

              {/* Name & Email */}
              <div style={{ flex: 1, minWidth: 150 }}>
                <div style={{ fontSize: 18, fontWeight: 800, color: "var(--text-primary)", marginBottom: 2 }}>
                  {displayName}
                </div>
                <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 6 }}>{email}</div>
                {/* Tier Badge */}
                <span style={{
                  display: "inline-flex", alignItems: "center", gap: 5,
                  fontSize: 12, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
                  background: tc.bg, color: tc.color, border: `1px solid ${tc.color}`,
                }}>
                  {tc.icon} {tc.label} Member
                </span>
              </div>

              {/* Logout button */}
              <button onClick={handleLogout} style={{
                padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer",
                border: "1px solid var(--border)", background: "transparent",
                color: "var(--text-muted)", transition: "all 0.15s",
              }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "var(--red)";
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--red)" }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
                  (e.currentTarget as HTMLElement).style.borderColor = "var(--border)" }}
              >
                ออกจากระบบ
              </button>
            </div>
          </div>

          {/* ── Subscription Info Card ── */}
          <div className="card">
            <div className="card-title">💳 ระดับสมาชิก</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "10px 12px", borderRadius: 8, background: tc.bg,
                border: `1px solid ${tc.color}40` }}>
                <span style={{ fontSize: 14, fontWeight: 700, color: tc.color }}>
                  {tc.icon} {tier}
                </span>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  {profileData?.subscription?.days_left != null
                    ? `เหลืออีก ${profileData.subscription.days_left} วัน`
                    : tier === "FREE" ? "ฟรีตลอดชีพ" : "Active"}
                </span>
              </div>

              {/* Feature limits */}
              {profileData?.limits && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 4 }}>
                  {[
                    { label: "Watchlist", val: `${profileData.limits.watchlist_items ?? "∞"} รายการ` },
                    { label: "Backtest", val: `${profileData.limits.backtest_years ?? 1} ปีย้อนหลัง` },
                    { label: "Scanner Top", val: `Top ${profileData.limits.scanner_top ?? 20}` },
                    { label: "Fundamental", val: profileData.limits.fundamental_access ? "✅ ใช้ได้" : "🔒 PRO เท่านั้น" },
                  ].map(r => (
                    <div key={r.label} style={{ display: "flex", justifyContent: "space-between",
                      fontSize: 12, padding: "4px 0", borderBottom: "1px solid var(--border)" }}>
                      <span style={{ color: "var(--text-muted)" }}>{r.label}</span>
                      <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{r.val}</span>
                    </div>
                  ))}
                </div>
              )}

              {tier === "FREE" && (
                <div style={{ marginTop: 8, padding: "10px 12px", borderRadius: 8,
                  background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)",
                  fontSize: 12, color: "#f59e0b", lineHeight: 1.6 }}>
                  ★ อัปเกรดเป็น PRO เพื่อปลดล็อก Backtest · สแกนหุ้น US · Fundamental ครบ
                </div>
              )}
            </div>
          </div>

          {/* ── Notification Settings Card ── */}
          <div className="card">
            <div className="card-title">🔔 การตั้งค่าแจ้งเตือน</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 600,
                  display: "block", marginBottom: 6 }}>
                  Line Notify Token
                </label>
                <input
                  type="text"
                  value={lineToken}
                  onChange={e => setLineToken(e.target.value)}
                  placeholder="วาง token จาก notify-bot.line.me"
                  style={{
                    width: "100%", padding: "8px 12px", borderRadius: 8, fontSize: 13,
                    background: "var(--bg-elevated)", border: "1px solid var(--border)",
                    color: "var(--text-primary)", outline: "none", boxSizing: "border-box",
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 600,
                  display: "block", marginBottom: 6 }}>
                  Telegram Chat ID
                </label>
                <input
                  type="text"
                  value={telegramId}
                  onChange={e => setTelegramId(e.target.value)}
                  placeholder="เช่น 123456789"
                  style={{
                    width: "100%", padding: "8px 12px", borderRadius: 8, fontSize: 13,
                    background: "var(--bg-elevated)", border: "1px solid var(--border)",
                    color: "var(--text-primary)", outline: "none", boxSizing: "border-box",
                  }}
                />
              </div>

              <button
                className="btn btn-primary"
                onClick={handleSave}
                disabled={saving}
                style={{ width: "100%", padding: "9px", fontSize: 13 }}
              >
                {saving ? "⏳ กำลังบันทึก..." : "💾 บันทึกการตั้งค่า"}
              </button>

              {saveMsg && (
                <div style={{
                  padding: "8px 12px", borderRadius: 8, fontSize: 12, fontWeight: 600,
                  background: saveMsg.ok ? "rgba(0,230,118,0.12)" : "rgba(255,82,82,0.12)",
                  color: saveMsg.ok ? "var(--green)" : "var(--red)",
                  border: `1px solid ${saveMsg.ok ? "var(--green)" : "var(--red)"}40`,
                }}>
                  {saveMsg.ok ? "✅" : "❌"} {saveMsg.text}
                </div>
              )}
            </div>
          </div>

          {/* ── Account Info Card ── */}
          <div className="card">
            <div className="card-title">👤 ข้อมูลบัญชี</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { label: "ชื่อผู้ใช้",   val: profileData?.username || authUser?.username || "-" },
                { label: "อีเมล",        val: email || "-" },
                { label: "วิธีเข้าสู่ระบบ", val: "Google OAuth" },
                { label: "สมัครสมาชิกเมื่อ", val: profileData?.profile?.created_at
                  ? new Date(profileData.profile.created_at).toLocaleDateString("th-TH", { dateStyle: "medium" })
                  : "-" },
              ].map(r => (
                <div key={r.label} style={{ display: "flex", justifyContent: "space-between",
                  fontSize: 13, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  <span style={{ color: "var(--text-muted)" }}>{r.label}</span>
                  <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{r.val}</span>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  )
}
