/**
 * pages/LoginPage.tsx
 * หน้า Login ด้วย Google — แสดงเมื่อยังไม่ได้ login
 */
import { useState, useEffect } from "react"
import { useAuth } from "../context/AuthContext"

const GOOGLE_CLIENT_ID = (import.meta as any).env.VITE_GOOGLE_CLIENT_ID || ""

declare global {
  interface Window {
    google?: any
    handleGoogleCredential?: (resp: any) => void
  }
}

export default function LoginPage() {
  const { loginWithGoogle } = useAuth()
  const [error, setError]   = useState("")
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return
    // โหลด Google GSI script
    const script = document.createElement("script")
    script.src = "https://accounts.google.com/gsi/client"
    script.async = true
    script.onload = initGoogle
    document.head.appendChild(script)
    return () => { document.head.removeChild(script) }
  }, [])

  function initGoogle() {
    if (!window.google || !GOOGLE_CLIENT_ID) return
    window.handleGoogleCredential = async (resp: any) => {
      setLoading(true); setError("")
      try {
        await loginWithGoogle(resp.credential)
      } catch (e: any) {
        setError(e.message || "Login ล้มเหลว กรุณาลองใหม่")
      }
      setLoading(false)
    }
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback:  window.handleGoogleCredential,
    })
    window.google.accounts.id.renderButton(
      document.getElementById("google-btn"),
      { theme:"filled_black", size:"large", text:"signin_with",
        shape:"pill", locale:"th", width:280 }
    )
  }

  const noClientId = !GOOGLE_CLIENT_ID

  return (
    <div style={{
      minHeight: "100vh", display: "flex", alignItems: "center",
      justifyContent: "center", background: "var(--bg-main, #0a1929)",
    }}>
      <div style={{
        width: "100%", maxWidth: 400,
        background: "var(--bg-surface, #1a2332)",
        border: "1px solid var(--border, #1e3a5f)",
        borderRadius: 20, padding: "48px 40px",
        textAlign: "center", boxShadow: "0 24px 64px rgba(0,0,0,.5)",
      }}>
        {/* Logo */}
        <div style={{ fontSize: 48, marginBottom: 8 }}>◈</div>
        <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent, #00d4ff)", marginBottom: 4 }}>
          Radar หุ้น
        </div>
        <div style={{ fontSize: 13, color: "var(--text-muted)", marginBottom: 40 }}>
          ระบบวิเคราะห์หุ้น AI-Powered
        </div>

        {/* Features */}
        <div style={{ marginBottom: 36, textAlign: "left" }}>
          {[
            "📡 สัญญาณซื้อขายจาก 5-Factor Engine",
            "🔥 Top Opportunities ทุกวัน",
            "⭐ Watchlist + ติดตามพอร์ต",
            "📊 Fundamental Data + Economic Calendar",
          ].map((f, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10,
              padding: "8px 0", fontSize: 13, color: "var(--text-secondary)",
              borderBottom: i < 3 ? "1px solid var(--border)" : "none" }}>
              {f}
            </div>
          ))}
        </div>

        {/* Plan badge */}
        <div style={{
          padding: "10px 16px", borderRadius: 10, marginBottom: 28,
          background: "rgba(0,212,255,.08)", border: "1px solid rgba(0,212,255,.2)",
          fontSize: 12, color: "var(--accent)",
        }}>
          🆓 สมัครฟรี · เริ่มต้นเป็น Free Plan ทันที · อัปเกรดทีหลังได้
        </div>

        {/* Google Button */}
        {noClientId ? (
          <div style={{ padding: "16px", background: "rgba(255,82,82,.1)",
            border: "1px solid rgba(255,82,82,.3)", borderRadius: 10,
            fontSize: 12, color: "var(--red)" }}>
            ⚠️ ยังไม่ได้ตั้งค่า VITE_GOOGLE_CLIENT_ID<br/>
            กรุณาเพิ่มใน .env.local แล้วรันใหม่
          </div>
        ) : (
          <div>
            <div id="google-btn" style={{ display: "flex", justifyContent: "center", marginBottom: 12 }} />
            {loading && (
              <div style={{ color: "var(--accent)", fontSize: 13 }}>⏳ กำลังเข้าสู่ระบบ...</div>
            )}
            {error && (
              <div style={{ color: "var(--red)", fontSize: 12, marginTop: 8 }}>❌ {error}</div>
            )}
          </div>
        )}

        <div style={{ marginTop: 24, fontSize: 11, color: "var(--text-muted)", lineHeight: 1.8 }}>
          การสมัครถือว่ายอมรับ Terms of Service<br/>
          ข้อมูลส่วนตัวได้รับการปกป้องตาม Privacy Policy
        </div>
      </div>
    </div>
  )
}
