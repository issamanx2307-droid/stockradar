import { useState, useEffect } from "react"
import { api } from "../api/client"
import { UserInfo } from "../api/types"

const TIER_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  FREE:    { label: "FREE Member",    color: "#6b7280", bg: "#f3f4f6" },
  PRO:     { label: "★ PRO Member",   color: "#3b82f6", bg: "#eff6ff" },
  PREMIUM: { label: "◆ PREMIUM",      color: "#8b5cf6", bg: "#f5f3ff" },
}

export default function Profile() {
  const [user, setUser]         = useState<UserInfo | null>(null)
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [lineToken, setLineToken]     = useState("")
  const [telegramId, setTelegramId]   = useState("")
  const [saved, setSaved]       = useState(false)

  useEffect(() => { loadProfile() }, [])

  async function loadProfile() {
    try {
      const data = await api.getProfile()
      setUser(data)
      setLineToken(data.profile.line_notify_token || "")
      setTelegramId(data.profile.telegram_chat_id || "")
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await api.updateProfile({
        line_notify_token: lineToken,
        telegram_chat_id: telegramId
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e) {
      alert("เกิดข้อผิดพลาดในการบันทึก")
    } finally {
      setSaving(false)
    }
  }

  if (loading) return (
    <div style={{ display:"flex", justifyContent:"center", alignItems:"center", height:"60vh", flexDirection:"column", gap:12 }}>
      <div className="loading-spinner" />
      <div style={{ color:"var(--text-muted)", fontSize:13 }}>กำลังโหลดโปรไฟล์...</div>
    </div>
  )
  if (!user) return <div className="p-8 text-center text-red-500">กรุณาเข้าสู่ระบบ</div>

  const tier      = (user.profile.tier || "FREE").toUpperCase()
  const tierCfg   = TIER_CONFIG[tier] || TIER_CONFIG.FREE
  const isGoogle  = user.profile.login_via_google
  const picUrl    = user.profile.picture_url

  return (
    <div className="profile-page p-8">
      <header className="page-header mb-8">
        <h1>โปรไฟล์ผู้ใช้</h1>
        <p className="text-muted">จัดการระดับสมาชิกและการแจ้งเตือน</p>
      </header>

      <div className="grid-2-col">
        {/* ── ข้อมูลสมาชิก ── */}
        <section className="card p-6">
          <h2 className="text-lg font-bold mb-4">ข้อมูลสมาชิก</h2>

          {/* รูปโปรไฟล์ */}
          <div style={{ display:"flex", alignItems:"center", gap:16, marginBottom:24 }}>
            {picUrl ? (
              <img
                src={picUrl}
                alt="Profile"
                width={64}
                height={64}
                style={{
                  borderRadius:"50%",
                  border:"3px solid #4285F4",
                  objectFit:"cover",
                  boxShadow:"0 2px 8px rgba(66,133,244,0.3)",
                }}
              />
            ) : (
              <div style={{
                width:64, height:64, borderRadius:"50%",
                background:"linear-gradient(135deg,#667eea,#764ba2)",
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:26, color:"#fff", fontWeight:"bold",
              }}>
                {(user.first_name || user.username || "?")[0].toUpperCase()}
              </div>
            )}
            <div>
              <div style={{ fontWeight:"bold", fontSize:16 }}>
                {user.first_name ? `${user.first_name} ${user.last_name || ""}`.trim() : user.username}
              </div>
              <div style={{ color:"var(--text-muted)", fontSize:13 }}>{user.email}</div>
              {isGoogle && (
                <div style={{
                  display:"inline-flex", alignItems:"center", gap:5,
                  background:"#e8f0fe", color:"#4285F4",
                  borderRadius:4, padding:"2px 8px", fontSize:12,
                  fontWeight:600, marginTop:4,
                }}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  สมัครด้วย Google
                </div>
              )}
            </div>
          </div>

          {/* ชื่อผู้ใช้ */}
          <div className="info-group mb-4">
            <label>ชื่อผู้ใช้</label>
            <div className="info-value">{user.username}</div>
          </div>

          {/* ระดับสมาชิก */}
          <div className="info-group mb-4">
            <label>ระดับสมาชิก</label>
            <div style={{
              display:"inline-block",
              background: tierCfg.bg,
              color: tierCfg.color,
              border: `1px solid ${tierCfg.color}`,
              borderRadius:6,
              padding:"4px 14px",
              fontWeight:700,
              fontSize:14,
            }}>
              {tierCfg.label}
            </div>
          </div>

          {!user.profile.is_pro && (
            <button className="btn btn-pro w-full mt-4">
              อัปเกรดเป็น PRO เพื่อใช้งาน Backtest และสแกนหุ้น US
            </button>
          )}
        </section>

        {/* ── การตั้งค่าแจ้งเตือน ── */}
        <section className="card p-6">
          <h2 className="text-lg font-bold mb-4">การตั้งค่าแจ้งเตือน</h2>
          <div className="form-group mb-4">
            <label>Line Notify Token</label>
            <input
              type="text"
              className="input-field"
              value={lineToken}
              onChange={(e) => setLineToken(e.target.value)}
              placeholder="ใส่ token จาก Line Notify"
            />
          </div>
          <div className="form-group mb-4">
            <label>Telegram Chat ID</label>
            <input
              type="text"
              className="input-field"
              value={telegramId}
              onChange={(e) => setTelegramId(e.target.value)}
              placeholder="ใส่ Chat ID จาก Telegram"
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
            style={{ width:"100%" }}
          >
            {saving ? "กำลังบันทึก..." : "บันทึกการตั้งค่า"}
          </button>
          {saved && (
            <div style={{
              marginTop:10, color:"#22c55e", fontWeight:600,
              textAlign:"center", fontSize:14,
            }}>
              ✅ บันทึกสำเร็จ
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
