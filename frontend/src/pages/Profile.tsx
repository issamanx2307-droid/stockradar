import { useState, useEffect } from "react"
import { api } from "../api/client"
import { useAuth } from "../context/AuthContext"
import { API_BASE } from "../api/config"

// ── Shared ────────────────────────────────────────────────────────────────────
const TIER_CONFIG: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  FREE:    { label: "FREE",    color: "var(--text-muted)", bg: "var(--bg-elevated)", icon: "◻" },
  PRO:     { label: "PRO",     color: "#f59e0b",           bg: "rgba(245,158,11,0.12)", icon: "★" },
  PREMIUM: { label: "PREMIUM", color: "var(--accent)",     bg: "var(--accent-dim)",   icon: "◈" },
}

function tabStyle(active: boolean) {
  return {
    padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer",
    border: `1.5px solid ${active ? "var(--accent)" : "var(--border)"}`,
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--accent)" : "var(--text-muted)",
    transition: "all 0.15s",
  } as React.CSSProperties
}

// ── Subscription Tab ──────────────────────────────────────────────────────────
interface Plan {
  name: string; name_th: string; icon: string
  price_thb: number; price_label: string; color: string
  watchlist_limit: number; signal_days: number
  fundamental_per_day: number; engine_scan_top: number
  backtest: boolean; portfolio_engine: boolean; scanner_formula: boolean
  features: string[]
}
interface StatusData {
  authenticated: boolean; username?: string
  tier: string; plan: Plan; expires_at: string | null
}

const PLAN_ORDER = ["free", "pro", "premium"]

function PlanCard({ planKey, plan, current, onSelect }: {
  planKey: string; plan: Plan; current: boolean; onSelect: () => void
}) {
  const isFree = planKey === "free"
  const isPremium = planKey === "premium"
  return (
    <div style={{
      border: `2px solid ${current ? plan.color : "var(--border)"}`,
      borderRadius: 16, padding: 24, position: "relative",
      background: current ? `${plan.color}08` : "var(--bg-surface)",
      transition: "all .2s", flex: 1, minWidth: 220,
      boxShadow: current ? `0 0 0 1px ${plan.color}44` : undefined,
    }}>
      {isPremium && (
        <div style={{ position: "absolute", top: -12, left: "50%", transform: "translateX(-50%)",
          background: plan.color, color: "#000", fontWeight: 800,
          fontSize: 11, padding: "3px 14px", borderRadius: 20, whiteSpace: "nowrap" }}>
          ✨ แนะนำ
        </div>
      )}
      {current && (
        <div style={{ position: "absolute", top: 12, right: 12,
          background: plan.color, color: "#000",
          fontSize: 10, fontWeight: 800, padding: "2px 8px", borderRadius: 10 }}>
          แผนปัจจุบัน
        </div>
      )}
      <div style={{ fontSize: 28, marginBottom: 6 }}>{plan.icon}</div>
      <div style={{ fontSize: 20, fontWeight: 800, color: plan.color }}>{plan.name_th}</div>
      <div style={{ fontSize: 22, fontWeight: 700, fontFamily: "var(--font-mono)", margin: "10px 0 4px" }}>
        {plan.price_thb === 0 ? "ฟรี" : `฿${plan.price_thb}`}
        {plan.price_thb > 0 && <span style={{ fontSize: 12, fontWeight: 400, color: "var(--text-muted)" }}>/เดือน</span>}
      </div>
      <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>{plan.price_label}</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6, marginBottom: 16 }}>
        {plan.features.map((f, i) => (
          <div key={i} style={{ display: "flex", gap: 8, fontSize: 12, alignItems: "flex-start" }}>
            <span style={{ color: plan.color, flexShrink: 0 }}>✓</span>
            <span style={{ color: "var(--text-secondary)" }}>{f}</span>
          </div>
        ))}
      </div>
      <div style={{ background: "var(--bg-elevated)", borderRadius: 8, padding: "8px 12px", marginBottom: 16, fontSize: 11 }}>
        {[
          { label: "Watchlist", val: plan.watchlist_limit === -1 ? "ไม่จำกัด" : `${plan.watchlist_limit} หุ้น` },
          { label: "Top Opps",  val: plan.engine_scan_top === -1 ? "ไม่จำกัด" : `Top ${plan.engine_scan_top}` },
          { label: "สัญญาณ",   val: `${plan.signal_days} วัน` },
        ].map(({ label, val }) => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between",
            padding: "3px 0", borderBottom: "1px solid var(--border)" }}>
            <span style={{ color: "var(--text-muted)" }}>{label}</span>
            <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: plan.color }}>{val}</span>
          </div>
        ))}
      </div>
      <button onClick={onSelect} disabled={current || isFree} style={{
        width: "100%", padding: "10px 0", borderRadius: 10, fontSize: 13,
        fontWeight: 700, cursor: current || isFree ? "default" : "pointer",
        border: `2px solid ${current ? plan.color : isFree ? "var(--border)" : plan.color}`,
        background: current ? plan.color : isFree ? "transparent" : `${plan.color}20`,
        color: current ? "#000" : isFree ? "var(--text-muted)" : plan.color,
        transition: "all .15s",
      }}>
        {current ? "✓ ใช้งานอยู่" : isFree ? "ใช้งานได้ฟรี" : `อัปเกรดเป็น ${plan.name_th}`}
      </button>
    </div>
  )
}

function SubscriptionTab() {
  const [status, setStatus]   = useState<StatusData | null>(null)
  const [plans, setPlans]     = useState<Record<string, Plan>>({})
  const [loading, setLoading] = useState(true)
  const [upgradeMsg, setUpgradeMsg] = useState("")

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/subscription/plans/`).then(r => r.json()),
      fetch(`${API_BASE}/subscription/status/`).then(r => r.json()),
    ]).then(([plansData, statusData]) => {
      setPlans(plansData.plans || {})
      setStatus(statusData)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  function handleUpgrade(planKey: string) {
    setUpgradeMsg(`ต้องการอัปเกรดเป็น ${plans[planKey]?.name_th} — กรุณาติดต่อ admin หรือชำระเงินผ่านช่องทางที่กำหนด`)
  }

  const currentTier = status?.tier || "free"

  return (
    <div>
      {status && (
        <div className="card" style={{ marginBottom: 20, display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 28 }}>{plans[currentTier]?.icon || "🆓"}</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>แผนปัจจุบัน</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: plans[currentTier]?.color || "var(--text-primary)" }}>
              {plans[currentTier]?.name_th || "ฟรี"}
              {status.authenticated && (
                <span style={{ fontSize: 12, fontWeight: 400, color: "var(--text-muted)", marginLeft: 8 }}>
                  ({status.username})
                </span>
              )}
            </div>
            {status.expires_at && (
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                หมดอายุ: {new Date(status.expires_at).toLocaleDateString("th-TH")}
              </div>
            )}
          </div>
          {currentTier !== "premium" && (
            <div style={{ fontSize: 11, color: "var(--yellow)", background: "rgba(255,214,0,.1)",
              padding: "6px 12px", borderRadius: 8, border: "1px solid rgba(255,214,0,.3)" }}>
              💡 อัปเกรดเพื่อปลดล็อคฟีเจอร์เพิ่มเติม
            </div>
          )}
        </div>
      )}

      {upgradeMsg && (
        <div style={{ marginBottom: 16, padding: "12px 16px", borderRadius: 10,
          background: "rgba(0,212,255,.08)", border: "1px solid rgba(0,212,255,.3)",
          color: "var(--accent)", fontSize: 13 }}>
          📩 {upgradeMsg}
        </div>
      )}

      {loading ? (
        <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลด...</span></div>
      ) : (
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
          {PLAN_ORDER.map(key => plans[key] ? (
            <PlanCard key={key} planKey={key} plan={plans[key]}
              current={currentTier === key} onSelect={() => handleUpgrade(key)} />
          ) : null)}
        </div>
      )}

      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-title">📊 เปรียบเทียบฟีเจอร์ทั้งหมด</div>
        <div style={{ overflowX: "auto" }}>
          <table className="data-table" style={{ minWidth: 460 }}>
            <thead>
              <tr>
                <th style={{ paddingLeft: 16, width: "40%" }}>ฟีเจอร์</th>
                {PLAN_ORDER.map(k => (
                  <th key={k} style={{ textAlign: "center", color: plans[k]?.color }}>
                    {plans[k]?.icon} {plans[k]?.name_th}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                { label: "Watchlist",         key: "watchlist_limit",     fmt: (v: any) => v === -1 ? "ไม่จำกัด" : `${v} หุ้น` },
                { label: "สัญญาณย้อนหลัง",   key: "signal_days",         fmt: (v: any) => `${v} วัน` },
                { label: "ผลสแกนที่เข้าเกณฑ์", key: "engine_scan_top",     fmt: (v: any) => v === -1 ? "ไม่จำกัด" : `Top ${v}` },
                { label: "Fundamental/วัน",   key: "fundamental_per_day", fmt: (v: any) => v === -1 ? "ไม่จำกัด" : `${v} ครั้ง` },
                { label: "Backtest Engine",   key: "backtest",            fmt: (v: any) => v ? "✅" : "❌" },
                { label: "Portfolio Engine",  key: "portfolio_engine",    fmt: (v: any) => v ? "✅" : "❌" },
                { label: "Scanner Formula",   key: "scanner_formula",     fmt: (v: any) => v ? "✅" : "❌" },
              ].map(({ label, key, fmt }) => (
                <tr key={key}>
                  <td style={{ paddingLeft: 16, fontSize: 13 }}>{label}</td>
                  {PLAN_ORDER.map(pk => (
                    <td key={pk} style={{ textAlign: "center", fontFamily: "var(--font-mono)",
                      fontSize: 13, color: plans[pk]?.color }}>
                      {plans[pk] ? fmt((plans[pk] as any)[key]) : "—"}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ marginTop: 16, textAlign: "center", fontSize: 12, color: "var(--text-muted)" }}>
        💬 ต้องการอัปเกรด? ติดต่อผ่านหน้า <b>ติดต่อเรา</b>
      </div>
    </div>
  )
}

// ── Profile / Settings Tab ────────────────────────────────────────────────────
function ProfileTab() {
  const { user: authUser, logout } = useAuth()
  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [saveMsg, setSaveMsg]   = useState<{ ok: boolean; text: string } | null>(null)
  const [profileData, setProfileData] = useState<any>(null)
  const [lineToken, setLineToken]     = useState("")
  const [telegramId, setTelegramId]   = useState("")

  useEffect(() => { loadProfile() }, [])

  async function loadProfile() {
    try {
      const data = await api.getProfile()
      setProfileData(data)
      setLineToken(data.profile?.line_notify_token || "")
      setTelegramId(data.profile?.telegram_chat_id || "")
    } catch (e) { console.error(e) }
    finally { setLoading(false) }
  }

  async function handleSave() {
    setSaving(true); setSaveMsg(null)
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

  if (loading) return <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลด...</span></div>

  const tier = (profileData?.profile?.tier || authUser?.tier || "FREE").toUpperCase()
  const tc = TIER_CONFIG[tier] || TIER_CONFIG.FREE
  const displayName = authUser?.first_name || authUser?.username || profileData?.username || "ผู้ใช้"
  const email = authUser?.email || profileData?.email || ""
  const picture = authUser?.picture

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>

      <div className="card" style={{ gridColumn: "1 / -1" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
          <div style={{ width: 60, height: 60, borderRadius: "50%", overflow: "hidden",
            background: "var(--accent-dim)", border: "2px solid var(--accent)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 24, fontWeight: 800, color: "var(--accent)", flexShrink: 0 }}>
            {picture
              ? <img src={picture} alt={displayName} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              : displayName.charAt(0).toUpperCase()}
          </div>
          <div style={{ flex: 1, minWidth: 150 }}>
            <div style={{ fontSize: 17, fontWeight: 800, color: "var(--text-primary)", marginBottom: 2 }}>{displayName}</div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>{email}</div>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 5,
              fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
              background: tc.bg, color: tc.color, border: `1px solid ${tc.color}` }}>
              {tc.icon} {tc.label} Member
            </span>
          </div>
          <button onClick={handleLogout} style={{
            padding: "8px 16px", borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: "pointer",
            border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)",
            transition: "all 0.15s",
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = "var(--red)"; (e.currentTarget as HTMLElement).style.borderColor = "var(--red)" }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = "var(--text-muted)"; (e.currentTarget as HTMLElement).style.borderColor = "var(--border)" }}
          >
            ออกจากระบบ
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-title">🔔 การตั้งค่าแจ้งเตือน</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            { label: "Line Notify Token", val: lineToken, set: setLineToken, placeholder: "วาง token จาก notify-bot.line.me" },
            { label: "Telegram Chat ID",  val: telegramId, set: setTelegramId, placeholder: "เช่น 123456789" },
          ].map(f => (
            <div key={f.label}>
              <label style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600,
                display: "block", marginBottom: 5 }}>{f.label}</label>
              <input type="text" value={f.val} onChange={e => f.set(e.target.value)}
                placeholder={f.placeholder}
                style={{ width: "100%", padding: "8px 12px", borderRadius: 8, fontSize: 12,
                  background: "var(--bg-elevated)", border: "1px solid var(--border)",
                  color: "var(--text-primary)", outline: "none", boxSizing: "border-box" }} />
            </div>
          ))}
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}
            style={{ width: "100%", padding: "9px", fontSize: 12 }}>
            {saving ? "⏳ กำลังบันทึก..." : "💾 บันทึกการตั้งค่า"}
          </button>
          {saveMsg && (
            <div style={{ padding: "7px 12px", borderRadius: 8, fontSize: 12, fontWeight: 600,
              background: saveMsg.ok ? "rgba(0,230,118,0.12)" : "rgba(255,82,82,0.12)",
              color: saveMsg.ok ? "var(--green)" : "var(--red)",
              border: `1px solid ${saveMsg.ok ? "var(--green)" : "var(--red)"}40` }}>
              {saveMsg.ok ? "✅" : "❌"} {saveMsg.text}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-title">👤 ข้อมูลบัญชี</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {[
            { label: "ชื่อผู้ใช้",        val: profileData?.username || authUser?.username || "-" },
            { label: "อีเมล",             val: email || "-" },
            { label: "วิธีเข้าสู่ระบบ",  val: "Google OAuth" },
            { label: "สมัครสมาชิกเมื่อ", val: profileData?.profile?.created_at
                ? new Date(profileData.profile.created_at).toLocaleDateString("th-TH", { dateStyle: "medium" })
                : "-" },
          ].map(r => (
            <div key={r.label} style={{ display: "flex", justifyContent: "space-between",
              fontSize: 12, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
              <span style={{ color: "var(--text-muted)" }}>{r.label}</span>
              <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{r.val}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

// ── Main Combined Page ────────────────────────────────────────────────────────
export default function Profile() {
  const [tab, setTab] = useState<"profile" | "subscription">("profile")

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">⚙️ บัญชี & สมาชิก</div>
        <div className="page-subtitle">โปรไฟล์ · การตั้งค่า · แผนสมาชิก</div>
      </div>
      <div className="page-body">

        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button style={tabStyle(tab === "profile")} onClick={() => setTab("profile")}>
            👤 โปรไฟล์ / ตั้งค่า
          </button>
          <button style={tabStyle(tab === "subscription")} onClick={() => setTab("subscription")}>
            💳 ระบบสมาชิก
          </button>
        </div>

        {tab === "profile"      && <ProfileTab />}
        {tab === "subscription" && <SubscriptionTab />}

      </div>
    </div>
  )
}
