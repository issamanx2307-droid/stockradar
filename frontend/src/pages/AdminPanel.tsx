/**
 * AdminPanel.tsx — หน้าควบคุมระบบสำหรับ Superadmin
 */
import { useState, useEffect } from "react"
import { API_BASE } from "../api/config"
import { useAuth } from "../context/AuthContext"
import { TermQuestionTicket } from "../api/types"

interface SystemStats {
  total_users: number
  total_signals: number
  total_news: number
  total_symbols: number
  total_prices: number
  last_signal_date: string | null
}

function QaPendingPanel({ token }: { token: string }) {
  const [questions, setQuestions] = useState<TermQuestionTicket[]>([])
  const [loadingQ, setLoadingQ] = useState(true)
  const [answering, setAnswering] = useState<number | null>(null)
  const [answerShort, setAnswerShort] = useState("")
  const [answerFull, setAnswerFull] = useState("")
  const [answerMsg, setAnswerMsg] = useState("")

  function loadPending() {
    setLoadingQ(true)
    fetch(`${API_BASE}/qa/pending/`, { headers: { Authorization: `Token ${token}` } })
      .then(r => r.json())
      .then(d => { setQuestions(d.results || []); setLoadingQ(false) })
      .catch(() => setLoadingQ(false))
  }

  useEffect(() => { loadPending() }, [token])

  async function submitAnswer(id: number) {
    if (!answerShort.trim()) return
    setAnswerMsg("")
    try {
      const res = await fetch(`${API_BASE}/qa/answer/${id}/`, {
        method: "PATCH",
        headers: { Authorization: `Token ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ answer_short: answerShort, answer_full: answerFull }),
      })
      if (res.ok) {
        setAnswerMsg("✅ ตอบสำเร็จ")
        setAnswering(null); setAnswerShort(""); setAnswerFull("")
        loadPending()
      } else {
        setAnswerMsg("❌ เกิดข้อผิดพลาด")
      }
    } catch {
      setAnswerMsg("❌ ไม่สามารถเชื่อมต่อได้")
    }
  }

  return (
    <div style={{ marginTop: 32 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: "#7a90a8", letterSpacing: 1, marginBottom: 16 }}>
        📬 คำถามรอตอบ ({loadingQ ? "..." : questions.length})
      </h2>
      {answerMsg && (
        <div style={{ marginBottom: 12, padding: "8px 14px", borderRadius: 8, fontSize: 13,
          background: answerMsg.startsWith("✅") ? "rgba(0,230,118,.08)" : "rgba(255,82,82,.08)",
          color: answerMsg.startsWith("✅") ? "#00e676" : "#ff5252",
          border: `1px solid ${answerMsg.startsWith("✅") ? "rgba(0,230,118,.25)" : "rgba(255,82,82,.25)"}`,
        }}>{answerMsg}</div>
      )}
      {loadingQ ? (
        <div style={{ color: "#5a6e80", fontSize: 13 }}>กำลังโหลด...</div>
      ) : questions.length === 0 ? (
        <div style={{ color: "#5a6e80", fontSize: 13, padding: "16px 0" }}>✅ ไม่มีคำถามรอตอบ</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {questions.map(q => (
            <div key={q.id} style={{
              padding: "14px 18px",
              background: "rgba(255,255,255,.03)",
              border: "1px solid rgba(255,255,255,.08)",
              borderRadius: 10,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: "#5a6e80", marginBottom: 4 }}>
                    #{q.id} · {new Date(q.created_at).toLocaleString("th-TH")}
                    {q.asked_by_username && <span> · 👤 {q.asked_by_username}</span>}
                  </div>
                  <div style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 600 }}>❓ {q.question}</div>
                </div>
                {answering !== q.id && (
                  <button
                    onClick={() => { setAnswering(q.id); setAnswerShort(""); setAnswerFull(""); setAnswerMsg("") }}
                    style={{
                      padding: "6px 14px", borderRadius: 8, fontSize: 12, fontWeight: 700,
                      background: "rgba(0,212,255,.12)", border: "1px solid rgba(0,212,255,.3)",
                      color: "#00d4ff", cursor: "pointer", flexShrink: 0,
                    }}>
                    ✏️ ตอบ
                  </button>
                )}
              </div>
              {answering === q.id && (
                <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
                  <input
                    placeholder="คำตอบสั้น (แสดงในแชท) *"
                    value={answerShort}
                    onChange={e => setAnswerShort(e.target.value)}
                    style={{
                      width: "100%", padding: "8px 12px", borderRadius: 7,
                      background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.12)",
                      color: "#e2e8f0", fontSize: 13,
                    }}
                  />
                  <textarea
                    placeholder="คำตอบเพิ่มเติม (ถ้ามี)"
                    value={answerFull}
                    onChange={e => setAnswerFull(e.target.value)}
                    rows={3}
                    style={{
                      width: "100%", padding: "8px 12px", borderRadius: 7,
                      background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.12)",
                      color: "#e2e8f0", fontSize: 13, resize: "vertical",
                    }}
                  />
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      onClick={() => submitAnswer(q.id)}
                      disabled={!answerShort.trim()}
                      style={{
                        padding: "7px 18px", borderRadius: 7, fontSize: 13, fontWeight: 700,
                        background: "rgba(0,230,118,.15)", border: "1px solid rgba(0,230,118,.3)",
                        color: "#00e676", cursor: "pointer",
                      }}>
                      ส่งคำตอบ
                    </button>
                    <button
                      onClick={() => setAnswering(null)}
                      style={{
                        padding: "7px 14px", borderRadius: 7, fontSize: 13,
                        background: "transparent", border: "1px solid rgba(255,255,255,.1)",
                        color: "#5a6e80", cursor: "pointer",
                      }}>
                      ยกเลิก
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

interface UserFlagRow {
  id: number
  username: string
  email: string
  tier: string
  can_use_portfolio: boolean
  date_joined: string
}

function UserPortfolioPanel({ token }: { token: string }) {
  const [users, setUsers] = useState<UserFlagRow[]>([])
  const [loading, setLoading] = useState(true)
  const [msg, setMsg] = useState("")

  useEffect(() => {
    fetch(`${API_BASE}/admin/users/`, {
      headers: { Authorization: `Token ${token}` },
    })
      .then(r => r.json())
      .then(d => { setUsers(d.results || []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [token])

  async function toggle(userId: number, current: boolean) {
    setMsg("")
    const res = await fetch(`${API_BASE}/admin/users/${userId}/portfolio/`, {
      method: "PATCH",
      headers: { Authorization: `Token ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ can_use_portfolio: !current }),
    })
    if (res.ok) {
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, can_use_portfolio: !current } : u))
      setMsg(`✅ อัปเดตสำเร็จ`)
    } else {
      setMsg("❌ เกิดข้อผิดพลาด")
    }
  }

  return (
    <div style={{ marginTop: 32 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: "#7a90a8", letterSpacing: 1, marginBottom: 16 }}>
        💼 สิทธิ์ Portfolio ({loading ? "..." : users.length} users)
      </h2>
      {msg && (
        <div style={{
          marginBottom: 12, padding: "8px 14px", borderRadius: 8, fontSize: 13,
          background: msg.startsWith("✅") ? "rgba(0,230,118,.08)" : "rgba(255,82,82,.08)",
          color: msg.startsWith("✅") ? "#00e676" : "#ff5252",
          border: `1px solid ${msg.startsWith("✅") ? "rgba(0,230,118,.25)" : "rgba(255,82,82,.25)"}`,
        }}>{msg}</div>
      )}
      {loading ? (
        <div style={{ color: "#5a6e80", fontSize: 13 }}>กำลังโหลด...</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {users.map(u => (
            <div key={u.id} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "10px 16px",
              background: "rgba(255,255,255,.03)",
              border: "1px solid rgba(255,255,255,.07)",
              borderRadius: 8,
            }}>
              <div>
                <span style={{ fontSize: 14, color: "#e2e8f0", fontWeight: 600 }}>{u.username}</span>
                <span style={{ fontSize: 12, color: "#5a6e80", marginLeft: 10 }}>{u.email}</span>
                <span style={{
                  fontSize: 11, marginLeft: 8, padding: "1px 7px", borderRadius: 10,
                  background: "rgba(0,212,255,.1)", color: "#00d4ff",
                }}>{u.tier}</span>
                <span style={{ fontSize: 11, color: "#3a4a58", marginLeft: 8 }}>{u.date_joined}</span>
              </div>
              <button
                onClick={() => toggle(u.id, u.can_use_portfolio)}
                style={{
                  padding: "5px 16px", borderRadius: 7, fontSize: 12, fontWeight: 700,
                  cursor: "pointer", transition: "all .15s",
                  background: u.can_use_portfolio ? "rgba(0,230,118,.15)" : "rgba(255,255,255,.05)",
                  border: `1px solid ${u.can_use_portfolio ? "rgba(0,230,118,.35)" : "rgba(255,255,255,.12)"}`,
                  color: u.can_use_portfolio ? "#00e676" : "#5a6e80",
                }}>
                {u.can_use_portfolio ? "✅ เปิดอยู่" : "🔒 ปิดอยู่"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
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

      {token && <QaPendingPanel token={token} />}
      {token && <UserPortfolioPanel token={token} />}
    </div>
  )
}
