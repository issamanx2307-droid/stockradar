/**
 * pages/Subscription.tsx
 * หน้าแสดง Pricing + สถานะ Plan ปัจจุบัน
 */
import { useState, useEffect } from "react"
import { API_BASE } from "../api/config"

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
      borderRadius: 16, padding: 28, position: "relative",
      background: current ? `${plan.color}08` : "var(--bg-surface)",
      transition: "all .2s", flex: 1, minWidth: 240,
      boxShadow: current ? `0 0 0 1px ${plan.color}44` : undefined,
    }}>
      {isPremium && (
        <div style={{
          position:"absolute", top:-12, left:"50%", transform:"translateX(-50%)",
          background: plan.color, color:"#000", fontWeight:800,
          fontSize:11, padding:"3px 14px", borderRadius:20, whiteSpace:"nowrap",
        }}>✨ แนะนำ</div>
      )}
      {current && (
        <div style={{
          position:"absolute", top:12, right:12,
          background: plan.color, color:"#000",
          fontSize:10, fontWeight:800, padding:"2px 8px", borderRadius:10,
        }}>แผนปัจจุบัน</div>
      )}

      <div style={{ fontSize:32, marginBottom:8 }}>{plan.icon}</div>
      <div style={{ fontSize:22, fontWeight:800, color: plan.color }}>{plan.name_th}</div>
      <div style={{ fontSize:24, fontWeight:700, fontFamily:"var(--font-mono)", margin:"12px 0 4px" }}>
        {plan.price_thb === 0 ? "ฟรี" : `฿${plan.price_thb}`}
        {plan.price_thb > 0 && <span style={{ fontSize:13, fontWeight:400, color:"var(--text-muted)" }}>/เดือน</span>}
      </div>
      <div style={{ fontSize:12, color:"var(--text-muted)", marginBottom:20 }}>{plan.price_label}</div>

      {/* Features */}
      <div style={{ display:"flex", flexDirection:"column", gap:8, marginBottom:24 }}>
        {plan.features.map((f, i) => (
          <div key={i} style={{ display:"flex", gap:8, fontSize:13, alignItems:"flex-start" }}>
            <span style={{ color: plan.color, flexShrink:0, marginTop:1 }}>✓</span>
            <span style={{ color:"var(--text-secondary)" }}>{f}</span>
          </div>
        ))}
      </div>

      {/* Limit summary */}
      <div style={{
        background:"var(--bg-elevated)", borderRadius:8, padding:"10px 14px",
        marginBottom:20, fontSize:12,
      }}>
        {[
          { label:"Watchlist", val: plan.watchlist_limit === -1 ? "ไม่จำกัด" : `${plan.watchlist_limit} หุ้น` },
          { label:"สัญญาณ",   val: `${plan.signal_days} วัน` },
          { label:"Top Opps", val: plan.engine_scan_top === -1 ? "ไม่จำกัด" : `Top ${plan.engine_scan_top}` },
        ].map(({ label, val }) => (
          <div key={label} style={{ display:"flex", justifyContent:"space-between", padding:"3px 0",
            borderBottom:"1px solid var(--border)" }}>
            <span style={{ color:"var(--text-muted)" }}>{label}</span>
            <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, color: plan.color }}>{val}</span>
          </div>
        ))}
      </div>

      <button
        onClick={onSelect}
        disabled={current || isFree}
        style={{
          width:"100%", padding:"12px 0", borderRadius:10, fontSize:14,
          fontWeight:700, cursor: current || isFree ? "default" : "pointer",
          border:`2px solid ${current ? plan.color : isFree ? "var(--border)" : plan.color}`,
          background: current ? plan.color : isFree ? "transparent" : `${plan.color}20`,
          color: current ? "#000" : isFree ? "var(--text-muted)" : plan.color,
          transition:"all .15s",
        }}
      >
        {current ? "✓ ใช้งานอยู่" : isFree ? "ใช้งานได้ฟรี" : `อัปเกรดเป็น ${plan.name_th}`}
      </button>
    </div>
  )
}

export default function Subscription() {
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
    }).catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  function handleUpgrade(planKey: string) {
    setUpgradeMsg(
      `ต้องการอัปเกรดเป็น ${plans[planKey]?.name_th} — กรุณาติดต่อ admin หรือชำระเงินผ่านช่องทางที่กำหนด`
    )
  }

  const currentTier = status?.tier || "free"

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">💳 ระบบสมาชิก</div>
        <div className="page-subtitle">เลือกแผนที่เหมาะสมกับการลงทุนของคุณ</div>
      </div>
      <div className="page-body">

        {/* Current Status */}
        {status && (
          <div className="card" style={{ marginBottom:24, display:"flex", alignItems:"center", gap:16 }}>
            <div style={{ fontSize:32 }}>{plans[currentTier]?.icon || "🆓"}</div>
            <div style={{ flex:1 }}>
              <div style={{ fontSize:13, color:"var(--text-muted)" }}>แผนปัจจุบัน</div>
              <div style={{ fontSize:20, fontWeight:700, color: plans[currentTier]?.color || "var(--text-primary)" }}>
                {plans[currentTier]?.name_th || "ฟรี"}
                {status.authenticated && <span style={{ fontSize:13, fontWeight:400, color:"var(--text-muted)", marginLeft:8 }}>({status.username})</span>}
              </div>
              {status.expires_at && (
                <div style={{ fontSize:12, color:"var(--text-muted)", marginTop:2 }}>
                  หมดอายุ: {new Date(status.expires_at).toLocaleDateString("th-TH")}
                </div>
              )}
            </div>
            {currentTier !== "premium" && (
              <div style={{ fontSize:12, color:"var(--yellow)", background:"rgba(255,214,0,.1)",
                padding:"6px 12px", borderRadius:8, border:"1px solid rgba(255,214,0,.3)" }}>
                💡 อัปเกรดเพื่อปลดล็อคฟีเจอร์เพิ่มเติม
              </div>
            )}
          </div>
        )}

        {/* Upgrade message */}
        {upgradeMsg && (
          <div style={{ marginBottom:20, padding:"14px 18px", borderRadius:10,
            background:"rgba(0,212,255,.08)", border:"1px solid rgba(0,212,255,.3)",
            color:"var(--accent)", fontSize:14 }}>
            📩 {upgradeMsg}
          </div>
        )}

        {/* Plan Cards */}
        {loading ? (
          <div className="loading-state"><div className="loading-spinner"/><span>กำลังโหลด...</span></div>
        ) : (
          <div style={{ display:"flex", gap:20, flexWrap:"wrap" }}>
            {PLAN_ORDER.map(key => plans[key] ? (
              <PlanCard
                key={key} planKey={key} plan={plans[key]}
                current={currentTier === key}
                onSelect={() => handleUpgrade(key)}
              />
            ) : null)}
          </div>
        )}

        {/* Feature Comparison Table */}
        <div className="card" style={{ marginTop:32 }}>
          <div className="card-title">📊 เปรียบเทียบฟีเจอร์ทั้งหมด</div>
          <div style={{ overflowX:"auto" }}>
            <table className="data-table" style={{ minWidth:500 }}>
              <thead>
                <tr>
                  <th style={{ paddingLeft:16, width:"40%" }}>ฟีเจอร์</th>
                  {PLAN_ORDER.map(k => (
                    <th key={k} style={{ textAlign:"center", color: plans[k]?.color }}>
                      {plans[k]?.icon} {plans[k]?.name_th}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  { label:"Watchlist", key:"watchlist_limit", fmt:(v: any) => v===-1?"ไม่จำกัด":`${v} หุ้น` },
                  { label:"สัญญาณย้อนหลัง", key:"signal_days", fmt:(v: any) => `${v} วัน` },
                  { label:"Top Opportunities", key:"engine_scan_top", fmt:(v: any) => v===-1?"ไม่จำกัด":`Top ${v}` },
                  { label:"Fundamental/วัน", key:"fundamental_per_day", fmt:(v: any) => v===-1?"ไม่จำกัด":`${v} ครั้ง` },
                  { label:"Backtest Engine", key:"backtest", fmt:(v: any) => v ? "✅" : "❌" },
                  { label:"Portfolio Engine", key:"portfolio_engine", fmt:(v: any) => v ? "✅" : "❌" },
                  { label:"Scanner Formula", key:"scanner_formula", fmt:(v: any) => v ? "✅" : "❌" },
                ].map(({ label, key, fmt }) => (
                  <tr key={key}>
                    <td style={{ paddingLeft:16, fontSize:13 }}>{label}</td>
                    {PLAN_ORDER.map(pk => (
                      <td key={pk} style={{ textAlign:"center", fontFamily:"var(--font-mono)",
                        fontSize:13, color: plans[pk]?.color }}>
                        {plans[pk] ? fmt((plans[pk] as any)[key]) : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Contact */}
        <div style={{ marginTop:24, textAlign:"center", fontSize:13, color:"var(--text-muted)" }}>
          💬 ต้องการอัปเกรดหรือมีคำถาม? ติดต่อผ่านหน้า <b>ติดต่อเรา</b>
        </div>

      </div>
    </div>
  )
}
