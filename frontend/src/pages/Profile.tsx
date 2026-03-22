import { useState, useEffect } from "react"
import { api } from "../api/client"
import { UserInfo } from "../api/types"

export default function Profile() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [lineToken, setLineToken] = useState("")
  const [telegramId, setTelegramId] = useState("")

  useEffect(() => {
    loadProfile()
  }, [])

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
      alert("บันทึกการตั้งค่าสำเร็จ")
    } catch (e) {
      alert("เกิดข้อผิดพลาดในการบันทึก")
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="p-8 text-center">กำลังโหลดโปรไฟล์...</div>
  if (!user) return <div className="p-8 text-center text-red-500">กรุณาเข้าสู่ระบบ</div>

  return (
    <div className="profile-page p-8">
      <header className="page-header mb-8">
        <h1>โปรไฟล์ผู้ใช้</h1>
        <p className="text-muted">จัดการระดับสมาชิกและการแจ้งเตือน</p>
      </header>

      <div className="grid-2-col">
        {/* ข้อมูลสมาชิก */}
        <section className="card p-6">
          <h2 className="text-lg font-bold mb-4">ข้อมูลสมาชิก</h2>
          <div className="info-group mb-4">
            <label>ชื่อผู้ใช้</label>
            <div className="info-value">{user.username}</div>
          </div>
          <div className="info-group mb-4">
            <label>อีเมล</label>
            <div className="info-value">{user.email}</div>
          </div>
          <div className="info-group mb-4">
            <label>ระดับสมาชิก</label>
            <div className={`tier-badge ${user.profile.tier.toLowerCase()}`}>
              {user.profile.tier === "PRO" ? "★ PRO Member" : "FREE Member"}
            </div>
          </div>
          {!user.profile.is_pro && (
            <button className="btn btn-pro w-full mt-4">
              อัปเกรดเป็น PRO เพื่อใช้งาน Backtest และสแกนหุ้น US
            </button>
          )}
        </section>

        {/* ตั้งค่าการแจ้งเตือน */}
        <section className="card p-6">
          <h2 className="text-lg font-bold mb-4">การตั้งค่าแจ้งเตือน (Alerts)</h2>
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
          >
            {saving ? "กำลังบันทึก..." : "บันทึกการตั้งค่า"}
          </button>
        </section>
      </div>
    </div>
  )
}
