/**
 * pages/LandingPage.tsx
 * Landing page สำหรับ radarhoon.com
 * — Hero / Features / Pricing / Footer
 * — TickerTape ดัชนีวิ่งด้านล่าง
 */
import { useState, useEffect, useRef } from "react"
import { useAuth } from "../context/AuthContext"
import { API_BASE } from "../api/config"
import TickerTape from "../components/TickerTape"

const GOOGLE_CLIENT_ID = (import.meta as any).env.VITE_GOOGLE_CLIENT_ID || ""

declare global {
  interface Window { google?: any; handleGoogleCredential?: (r: any) => void }
}

// ── Sub-components ─────────────────────────────────────────────────────────────
function StatCard({ value, label, color = "#00d4ff" }: { value: string; label: string; color?: string }) {
  return (
    <div style={{
      textAlign: "center", padding: "24px 20px",
      background: "rgba(255,255,255,.03)",
      border: "1px solid rgba(255,255,255,.06)",
      borderRadius: 16, flex: 1, minWidth: 140,
    }}>
      <div style={{ fontSize: 32, fontWeight: 800, color, letterSpacing: -1 }}>{value}</div>
      <div style={{ fontSize: 13, color: "#7a90a8", marginTop: 6 }}>{label}</div>
    </div>
  )
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div style={{
      padding: "28px 24px",
      background: "rgba(255,255,255,.03)",
      border: "1px solid rgba(255,255,255,.07)",
      borderRadius: 16,
      transition: "border-color .2s, transform .2s",
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLElement).style.borderColor = "rgba(0,212,255,.4)"
        ;(e.currentTarget as HTMLElement).style.transform = "translateY(-3px)"
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,.07)"
        ;(e.currentTarget as HTMLElement).style.transform = "translateY(0)"
      }}
    >
      <div style={{ fontSize: 36, marginBottom: 14 }}>{icon}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: "#e2e8f0", marginBottom: 10 }}>{title}</div>
      <div style={{ fontSize: 14, color: "#6a8099", lineHeight: 1.7 }}>{desc}</div>
    </div>
  )
}

function PlanCard({
  name, thaiName, price, color, features, highlight, btnId,
}: {
  name: string; thaiName: string; price: string; color: string
  features: string[]; highlight?: boolean; btnId: string
}) {
  return (
    <div style={{
      flex: 1, minWidth: 240,
      padding: "32px 28px",
      background: highlight ? `rgba(0,212,255,.07)` : "rgba(255,255,255,.03)",
      border: `1px solid ${highlight ? "rgba(0,212,255,.5)" : "rgba(255,255,255,.07)"}`,
      borderRadius: 20,
      position: "relative",
      transition: "transform .2s",
    }}>
      {highlight && (
        <div style={{
          position: "absolute", top: -14, left: "50%", transform: "translateX(-50%)",
          background: "#00d4ff", color: "#0a0e17",
          fontSize: 11, fontWeight: 800, padding: "4px 16px",
          borderRadius: 20, letterSpacing: 1, whiteSpace: "nowrap",
        }}>
          ยอดนิยม
        </div>
      )}
      <div style={{ fontSize: 13, color, fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>{name}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "#e2e8f0", marginBottom: 4 }}>{thaiName}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color, marginBottom: 20 }}>{price}</div>
      <div style={{ marginBottom: 24 }}>
        {features.map((f, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "6px 0", fontSize: 13, color: "#a0b4c8",
            borderBottom: "1px solid rgba(255,255,255,.05)",
          }}>
            <span style={{ color, fontSize: 10 }}>✦</span> {f}
          </div>
        ))}
      </div>
      <div id={btnId} style={{ display: "flex", justifyContent: "center" }} />
    </div>
  )
}

// ── Signal types ──────────────────────────────────────────────────────────────
interface TopSignal {
  id: number
  symbol_code: string
  symbol_name?: string
  exchange?: string
  score: number
  signal_type: string
  direction: string
  price?: number
  stop_loss?: number
}

function sigLabel(t: string) {
  const map: Record<string, string> = {
    BUY: "BUY", STRONG_BUY: "STRONG", GOLDEN_CROSS: "CROSS",
    EMA_ALIGNMENT: "ALIGN", BREAKOUT: "BREAK", OVERSOLD: "OVS",
  }
  return map[t] ?? t.slice(0, 5)
}
function sigColor(d: string) { return d === "LONG" ? "#00e676" : "#ff5252" }

// ── Main Component ─────────────────────────────────────────────────────────────
export default function LandingPage() {
  const { loginWithGoogle } = useAuth()
  const [error, setError] = useState("")
  const [loginLoading, setLoginLoading] = useState(false)
  const [topSignals, setTopSignals] = useState<TopSignal[]>([])
  const [lastUpdate, setLastUpdate] = useState("")
  const [blinkIdx, setBlinkIdx] = useState(0)
  const heroRef = useRef<HTMLDivElement>(null)

  // ── Google login init ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return
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
      setLoginLoading(true); setError("")
      try { await loginWithGoogle(resp.credential) }
      catch (e: any) { setError(e.message || "Login ล้มเหลว กรุณาลองใหม่") }
      setLoginLoading(false)
    }
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: window.handleGoogleCredential,
    })
    // render ปุ่ม login ทุก container
    ;["google-btn-hero", "google-btn-cta"].forEach(id => {
      const el = document.getElementById(id)
      if (el) {
        window.google!.accounts.id.renderButton(el, {
          theme: "filled_black", size: "large",
          text: "signin_with", shape: "pill", locale: "th", width: 260,
        })
      }
    })
  }

  // ── Top Signals fetch (auto-update ทุก 5 นาที) ───────────────────────────────
  useEffect(() => {
    let cancelled = false
    async function loadTop() {
      try {
        const res = await fetch(`${API_BASE}/dashboard/`)
        const d = await res.json()
        if (!cancelled && d.top_bullish?.length) {
          setTopSignals(d.top_bullish.slice(0, 7))
          setLastUpdate(new Date().toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" }))
        }
      } catch { /* silent */ }
    }
    loadTop()
    const iv = setInterval(loadTop, 5 * 60 * 1000)
    return () => { cancelled = true; clearInterval(iv) }
  }, [])

  // ── Blink row highlight ────────────────────────────────────────────────────
  useEffect(() => {
    const iv = setInterval(() => setBlinkIdx(i => (i + 1) % 7), 2000)
    return () => clearInterval(iv)
  }, [])

  // ── Scroll-spy animation (Intersection Observer) ─────────────────────────────
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => entries.forEach(e => {
        if (e.isIntersecting) e.target.classList.add("lp-visible")
      }),
      { threshold: 0.12 }
    )
    document.querySelectorAll(".lp-fade").forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [])

  const noGoogleId = !GOOGLE_CLIENT_ID

  return (
    <div style={{ fontFamily: "'IBM Plex Sans Thai', sans-serif", background: "#080d18", color: "#e2e8f0", minHeight: "100vh" }}>

      {/* ── CSS ─────────────────────────────────────────────────── */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700;800&display=swap');
        .lp-fade { opacity: 0; transform: translateY(28px); transition: opacity .6s ease, transform .6s ease; }
        .lp-visible { opacity: 1 !important; transform: translateY(0) !important; }
        .lp-fade-delay-1 { transition-delay: .1s; }
        .lp-fade-delay-2 { transition-delay: .2s; }
        .lp-fade-delay-3 { transition-delay: .3s; }
        .lp-fade-delay-4 { transition-delay: .4s; }
        @keyframes heroFloat {
          0%,100% { transform: translateY(0px); }
          50%      { transform: translateY(-12px); }
        }
        @keyframes glowPulse {
          0%,100% { opacity: .25; }
          50%      { opacity: .55; }
        }
        @keyframes spinSlow {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes blinkDot {
          0%,100% { opacity:1; } 50% { opacity:.2; }
        }
        .hero-glow {
          position: absolute; border-radius: 50%;
          background: radial-gradient(circle, rgba(0,212,255,.35) 0%, transparent 70%);
          animation: glowPulse 4s ease-in-out infinite;
          pointer-events: none;
        }
        .lp-nav-link {
          color: #7a90a8; font-size: 14px; text-decoration: none;
          transition: color .2s; cursor: pointer; background: none; border: none;
        }
        .lp-nav-link:hover { color: #00d4ff; }
        .lp-btn-primary {
          background: linear-gradient(135deg, #00d4ff, #0090cc);
          color: #0a0e17; border: none; border-radius: 50px;
          padding: 12px 28px; font-size: 15px; font-weight: 700;
          cursor: pointer; transition: transform .15s, box-shadow .15s;
          box-shadow: 0 4px 20px rgba(0,212,255,.3);
        }
        .lp-btn-primary:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 28px rgba(0,212,255,.45);
        }
        .lp-section { padding: 80px 0; }
        .lp-container { max-width: 1140px; margin: 0 auto; padding: 0 24px; }
        @keyframes rowBlink {
          0%,100% { background: transparent; }
          50%      { background: rgba(0,212,255,.06); }
        }
        .signal-row-blink { animation: rowBlink 1s ease-in-out; }
        @media (max-width: 900px) {
          .lp-hero-title { font-size: 32px !important; }
          .lp-hero-layout { flex-direction: column !important; }
          .lp-hero-card { width: 100% !important; max-width: 100% !important; position: static !important; }
          .lp-grid-4 { grid-template-columns: repeat(2, 1fr) !important; }
          .lp-grid-3 { grid-template-columns: 1fr !important; }
          .lp-flex-plans { flex-direction: column !important; }
          .lp-hide-mobile { display: none !important; }
          .lp-stats-flex { flex-wrap: wrap !important; }
        }
      `}</style>

      {/* ── NAVBAR ─────────────────────────────────────────────────── */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 999,
        background: "rgba(8,13,24,.85)", backdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255,255,255,.07)",
        padding: "0 24px", height: 62,
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 26, color: "#00d4ff", lineHeight: 1 }}>◈</span>
          <div>
            <span style={{ fontSize: 18, fontWeight: 800, color: "#e2e8f0" }}>Radar</span>
            <span style={{ fontSize: 18, fontWeight: 800, color: "#00d4ff" }}>หุ้น</span>
          </div>
          <span style={{
            fontSize: 9, fontWeight: 700, color: "#00d4ff",
            background: "rgba(0,212,255,.12)", border: "1px solid rgba(0,212,255,.3)",
            borderRadius: 4, padding: "1px 6px", letterSpacing: 1, alignSelf: "flex-end", marginBottom: 2,
          }}>
            AI
          </span>
        </div>

        {/* Nav links */}
        <div className="lp-hide-mobile" style={{ display: "flex", alignItems: "center", gap: 28 }}>
          {[
            ["#features", "ฟีเจอร์"], ["#pricing", "ราคา"],
          ].map(([href, label]) => (
            <a key={href} href={href} className="lp-nav-link">{label}</a>
          ))}
        </div>

        {/* CTA */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              fontSize: 10, fontWeight: 700, color: "#00e676",
              animation: "blinkDot 2s ease-in-out infinite",
              display: "flex", alignItems: "center", gap: 5,
            }}
            className="lp-hide-mobile"
          >
            <span>●</span> LIVE
          </div>
          {noGoogleId ? (
            <span style={{ fontSize: 12, color: "#ff5252" }}>VITE_GOOGLE_CLIENT_ID missing</span>
          ) : (
            <div id="google-btn-nav" style={{ transform: "scale(.85)", transformOrigin: "right center" }}>
              {/* rendered by GSI */}
            </div>
          )}
        </div>
      </nav>

      {/* ── HERO ─────────────────────────────────────────────────────── */}
      <section ref={heroRef} style={{
        position: "relative", overflow: "hidden",
        minHeight: "100vh", display: "flex", alignItems: "center",
        paddingTop: 62,
      }}>
        {/* Background glows */}
        <div className="hero-glow" style={{ width: 600, height: 600, top: -100, left: -150 }} />
        <div className="hero-glow" style={{ width: 400, height: 400, bottom: 0, right: -80, animationDelay: "2s" }} />

        {/* Grid pattern overlay */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: "linear-gradient(rgba(0,212,255,.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,.03) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          pointerEvents: "none",
        }} />

        <div className="lp-container lp-hero-layout" style={{
          position: "relative", zIndex: 1,
          padding: "80px 24px",
          display: "flex", alignItems: "center", gap: 48,
        }}>

          {/* ── LEFT: TOP OPPORTUNITIES CARD ── */}
          <div className="lp-hero-card lp-fade" style={{
            flexShrink: 0, width: 400,
            animation: "heroFloat 5s ease-in-out infinite",
          }}>
            <div style={{
              background: "rgba(10,18,35,.95)", backdropFilter: "blur(16px)",
              border: "1px solid rgba(0,212,255,.25)",
              borderRadius: 20,
              boxShadow: "0 24px 80px rgba(0,0,0,.6), 0 0 60px rgba(0,212,255,.1)",
              overflow: "hidden",
            }}>
              {/* Card header */}
              <div style={{
                padding: "16px 22px",
                borderBottom: "1px solid rgba(0,212,255,.12)",
                background: "rgba(0,212,255,.04)",
                display: "flex", alignItems: "center", justifyContent: "space-between",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%", background: "#00e676",
                    boxShadow: "0 0 8px #00e676",
                    animation: "blinkDot 1.2s ease-in-out infinite",
                  }} />
                  <span style={{ fontSize: 12, fontWeight: 800, color: "#e2e8f0", letterSpacing: 1 }}>
                    TOP OPPORTUNITIES
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {lastUpdate && (
                    <span style={{ fontSize: 10, color: "#4a5a70" }}>อัปเดต {lastUpdate}</span>
                  )}
                  <span style={{
                    fontSize: 10, fontWeight: 700, color: "#00e676",
                    background: "rgba(0,230,118,.1)", border: "1px solid rgba(0,230,118,.25)",
                    borderRadius: 4, padding: "2px 7px",
                  }}>LIVE</span>
                </div>
              </div>

              {/* Column headers */}
              <div style={{
                display: "grid", gridTemplateColumns: "32px 1fr 60px 56px",
                padding: "8px 22px", gap: 8,
                fontSize: 10, fontWeight: 700, color: "#3a5a70", letterSpacing: 1,
                borderBottom: "1px solid rgba(255,255,255,.04)",
              }}>
                <span>#</span><span>หุ้น</span><span style={{ textAlign: "center" }}>SIGNAL</span><span style={{ textAlign: "right" }}>SCORE</span>
              </div>

              {/* Signal rows */}
              <div style={{ padding: "4px 0" }}>
                {(topSignals.length > 0 ? topSignals : Array(7).fill(null)).map((s, i) => {
                  const isLoading = !s
                  const isBlink = !isLoading && i === blinkIdx % topSignals.length
                  return (
                    <div key={i} className={isBlink ? "signal-row-blink" : ""} style={{
                      display: "grid", gridTemplateColumns: "32px 1fr 60px 56px",
                      alignItems: "center", gap: 8,
                      padding: "10px 22px",
                      borderBottom: "1px solid rgba(255,255,255,.03)",
                      fontSize: 13,
                      transition: "background .3s",
                    }}>
                      {/* Rank */}
                      <span style={{
                        fontSize: 11, fontWeight: 700,
                        color: i === 0 ? "#ffd740" : i === 1 ? "#a0a0a0" : i === 2 ? "#cd7f32" : "#2a3a50",
                      }}>
                        {isLoading ? "—" : `${i + 1}`}
                      </span>

                      {/* Symbol + exchange */}
                      <div>
                        {isLoading ? (
                          <div style={{ width: 60, height: 12, background: "rgba(255,255,255,.05)", borderRadius: 4 }} />
                        ) : (
                          <>
                            <div style={{ fontWeight: 700, color: "#d8e8f0", fontSize: 14 }}>{s.symbol_code}</div>
                            <div style={{ fontSize: 10, color: "#3a5a70", marginTop: 1 }}>{s.symbol_name ?? s.exchange ?? ""}</div>
                          </>
                        )}
                      </div>

                      {/* Signal badge */}
                      <div style={{ textAlign: "center" }}>
                        {!isLoading && (
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: "3px 7px", borderRadius: 5,
                            background: `${sigColor(s.direction)}15`,
                            color: sigColor(s.direction),
                            border: `1px solid ${sigColor(s.direction)}35`,
                            letterSpacing: .3,
                          }}>
                            {sigLabel(s.signal_type)}
                          </span>
                        )}
                      </div>

                      {/* Score bar */}
                      <div style={{ textAlign: "right" }}>
                        {isLoading ? (
                          <div style={{ width: 36, height: 12, background: "rgba(255,255,255,.05)", borderRadius: 4, marginLeft: "auto" }} />
                        ) : (
                          <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 3 }}>
                            <span style={{
                              fontFamily: "monospace", fontWeight: 800, fontSize: 14,
                              color: s.score >= 85 ? "#00e676" : s.score >= 70 ? "#ffd740" : "#7a90a8",
                            }}>
                              {s.score}
                            </span>
                            <div style={{ width: 40, height: 3, background: "rgba(255,255,255,.08)", borderRadius: 2 }}>
                              <div style={{
                                width: `${s.score}%`, height: "100%", borderRadius: 2,
                                background: s.score >= 85 ? "#00e676" : s.score >= 70 ? "#ffd740" : "#448aff",
                              }} />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Card footer */}
              <div style={{
                padding: "12px 22px",
                borderTop: "1px solid rgba(255,255,255,.04)",
                display: "flex", justifyContent: "space-between", alignItems: "center",
              }}>
                <span style={{ fontSize: 11, color: "#2a3a50" }}>
                  {topSignals.length > 0 ? "ข้อมูลจริงจากระบบ" : "กำลังโหลด..."}
                </span>
                <span style={{ fontSize: 11, color: "#00d4ff", cursor: "pointer" }}>
                  ดูทั้งหมด →
                </span>
              </div>
            </div>
          </div>

          {/* ── RIGHT: HEADLINE + CTA ── */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Badge */}
            <div className="lp-fade lp-fade-delay-1" style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              background: "rgba(0,212,255,.08)", border: "1px solid rgba(0,212,255,.25)",
              borderRadius: 50, padding: "6px 16px", marginBottom: 28,
              fontSize: 13, color: "#00d4ff",
            }}>
              <span style={{ animation: "blinkDot 1.5s ease-in-out infinite", fontSize: 8 }}>●</span>
              ระบบวิเคราะห์หุ้น AI — อัปเดตทุกวัน
            </div>

            {/* Headline */}
            <h1 className="lp-fade lp-fade-delay-1 lp-hero-title" style={{
              fontSize: 52, fontWeight: 800, lineHeight: 1.2,
              margin: "0 0 20px", letterSpacing: -1.5,
            }}>
              วิเคราะห์หุ้นอย่าง{" "}
              <span style={{
                color: "transparent",
                backgroundImage: "linear-gradient(135deg, #00d4ff, #00e676)",
                WebkitBackgroundClip: "text", backgroundClip: "text",
              }}>
                มืออาชีพ
              </span>
              <br />ด้วย AI-Powered Engine
            </h1>

            {/* Subheadline */}
            <p className="lp-fade lp-fade-delay-2" style={{
              fontSize: 17, color: "#7a90a8", lineHeight: 1.8,
              margin: "0 0 32px",
            }}>
              สแกนกว่า <strong style={{ color: "#e2e8f0" }}>10,000+ หุ้น</strong> ทั่วโลก — ตลาดหุ้นไทย (SET) และ US Market
              พร้อมสัญญาณซื้อขายจาก <strong style={{ color: "#e2e8f0" }}>5-Factor Engine</strong> และข้อมูล Fundamental แบบเรียลไทม์
            </p>

            {/* Feature pills */}
            <div className="lp-fade lp-fade-delay-2" style={{
              display: "flex", flexWrap: "wrap", gap: 10, marginBottom: 40,
            }}>
              {["📡 สัญญาณซื้อขาย", "🔥 Top Opportunities", "📊 Backtest", "💼 Portfolio", "📰 ข่าว & Sentiment"].map(f => (
                <span key={f} style={{
                  padding: "7px 16px", borderRadius: 20,
                  background: "rgba(255,255,255,.05)",
                  border: "1px solid rgba(255,255,255,.1)",
                  fontSize: 13, color: "#a0b4c8",
                }}>
                  {f}
                </span>
              ))}
            </div>

            {/* CTA */}
            <div className="lp-fade lp-fade-delay-3" style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
              {noGoogleId ? (
                <div style={{
                  padding: "14px 20px", background: "rgba(255,82,82,.1)",
                  border: "1px solid rgba(255,82,82,.3)", borderRadius: 12,
                  fontSize: 13, color: "#ff5252",
                }}>
                  ⚠️ กรุณาตั้งค่า VITE_GOOGLE_CLIENT_ID ใน .env.local
                </div>
              ) : (
                <div>
                  <div id="google-btn-hero" style={{ marginBottom: 8 }} />
                  {loginLoading && <div style={{ fontSize: 13, color: "#00d4ff" }}>⏳ กำลังเข้าสู่ระบบ...</div>}
                  {error && <div style={{ fontSize: 12, color: "#ff5252" }}>❌ {error}</div>}
                </div>
              )}
              <div style={{ fontSize: 12, color: "#4a5a70" }}>
                ✓ สมัครฟรี &nbsp; ✓ ไม่ต้องใส่บัตรเครดิต &nbsp; ✓ เริ่มใช้งานทันที
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ── STATS ───────────────────────────────────────────────────── */}
      <section style={{ padding: "40px 0", borderTop: "1px solid rgba(255,255,255,.05)", borderBottom: "1px solid rgba(255,255,255,.05)" }}>
        <div className="lp-container">
          <div className="lp-fade lp-stats-flex" style={{ display: "flex", gap: 16 }}>
            <StatCard value="10,000+" label="หุ้นที่ติดตาม" color="#00d4ff" />
            <StatCard value="5 ปัจจัย" label="วิเคราะห์ต่อวัน" color="#00e676" />
            <StatCard value="SET + US" label="ตลาดหุ้นที่รองรับ" color="#ffd740" />
            <StatCard value="ฟรี" label="เริ่มต้นใช้งาน" color="#e040fb" />
          </div>
        </div>
      </section>

      {/* ── FEATURES ────────────────────────────────────────────────── */}
      <section id="features" className="lp-section">
        <div className="lp-container">
          <div className="lp-fade" style={{ textAlign: "center", marginBottom: 56 }}>
            <div style={{ fontSize: 13, color: "#00d4ff", fontWeight: 700, letterSpacing: 2, marginBottom: 12 }}>
              FEATURES
            </div>
            <h2 style={{ fontSize: 36, fontWeight: 800, margin: 0, letterSpacing: -.5 }}>
              ทุกเครื่องมือที่นักลงทุนต้องการ
            </h2>
            <p style={{ fontSize: 16, color: "#6a8099", marginTop: 12 }}>
              ออกแบบมาสำหรับนักลงทุนรายย่อยที่ต้องการข้อมูลระดับ Professional
            </p>
          </div>

          <div className="lp-grid-4 lp-fade lp-fade-delay-1" style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 20,
          }}>
            <FeatureCard
              icon="📡"
              title="สัญญาณซื้อขาย AI"
              desc="5-Factor Engine วิเคราะห์ EMA, RSI, MACD, Bollinger Bands, ADX พร้อม Stop Loss อัตโนมัติ"
            />
            <FeatureCard
              icon="🔥"
              title="Top Opportunities"
              desc="สแกนหาโอกาสซื้อขายดีที่สุดประจำวัน คัดกรองจากกว่า 10,000 หุ้นทั่วโลก"
            />
            <FeatureCard
              icon="⏪"
              title="Backtest Engine"
              desc="ทดสอบกลยุทธ์ย้อนหลังได้ถึง 5 ปี พร้อม Win Rate, Max Drawdown และ Sharpe Ratio"
            />
            <FeatureCard
              icon="📰"
              title="ข่าว & Sentiment"
              desc="วิเคราะห์ความรู้สึกตลาดจากข่าวการเงินแบบเรียลไทม์ ทั้งไทยและต่างประเทศ"
            />
            <FeatureCard
              icon="📊"
              title="Fundamental Data"
              desc="ข้อมูลพื้นฐานบริษัท P/E, P/BV, ROE, EPS งบการเงิน สำหรับสมาชิก PRO/PREMIUM"
            />
            <FeatureCard
              icon="📅"
              title="ปฏิทินเศรษฐกิจ"
              desc="ติดตามเหตุการณ์สำคัญทางเศรษฐกิจทั่วโลก FED, GDP, ดอกเบี้ย ก่อนตลาดขยับ"
            />
          </div>
        </div>
      </section>

      {/* ── HOW IT WORKS ────────────────────────────────────────────── */}
      <section style={{ padding: "60px 0", background: "rgba(255,255,255,.015)", borderTop: "1px solid rgba(255,255,255,.05)" }}>
        <div className="lp-container">
          <div className="lp-fade" style={{ textAlign: "center", marginBottom: 48 }}>
            <div style={{ fontSize: 13, color: "#ffd740", fontWeight: 700, letterSpacing: 2, marginBottom: 10 }}>
              HOW IT WORKS
            </div>
            <h2 style={{ fontSize: 32, fontWeight: 800, margin: 0 }}>เริ่มต้น 3 ขั้นตอน</h2>
          </div>
          <div className="lp-grid-3" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 28 }}>
            {[
              { num: "01", title: "สมัครฟรี", desc: "Login ด้วย Google Account ไม่ต้องกรอกข้อมูลเพิ่ม พร้อมใช้ทันที", color: "#00d4ff" },
              { num: "02", title: "เลือกหุ้นที่สนใจ", desc: "เพิ่มหุ้นใน Watchlist หรือใช้ Scanner ค้นหาโอกาสที่เหมาะสม", color: "#00e676" },
              { num: "03", title: "รับสัญญาณอัตโนมัติ", desc: "ระบบ AI วิเคราะห์และส่งสัญญาณซื้อขายพร้อม Stop Loss ทุกวัน", color: "#ffd740" },
            ].map((s, i) => (
              <div key={i} className={`lp-fade lp-fade-delay-${i + 1}`} style={{ textAlign: "center", padding: "8px 16px" }}>
                <div style={{
                  fontSize: 42, fontWeight: 900, color: "transparent",
                  backgroundImage: `linear-gradient(135deg, ${s.color}, transparent)`,
                  WebkitBackgroundClip: "text", backgroundClip: "text",
                  marginBottom: 16, lineHeight: 1,
                }}>
                  {s.num}
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 10, color: "#e2e8f0" }}>{s.title}</div>
                <div style={{ fontSize: 14, color: "#6a8099", lineHeight: 1.7 }}>{s.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING ─────────────────────────────────────────────────── */}
      <section id="pricing" style={{ padding: "80px 0", background: "rgba(255,255,255,.015)", borderTop: "1px solid rgba(255,255,255,.05)" }}>
        <div className="lp-container">
          <div className="lp-fade" style={{ textAlign: "center", marginBottom: 52 }}>
            <div style={{ fontSize: 13, color: "#e040fb", fontWeight: 700, letterSpacing: 2, marginBottom: 10 }}>
              PRICING
            </div>
            <h2 style={{ fontSize: 36, fontWeight: 800, margin: 0 }}>เลือกแผนที่เหมาะกับคุณ</h2>
            <p style={{ fontSize: 15, color: "#6a8099", marginTop: 12 }}>
              ไม่มีค่าธรรมเนียมซ่อนเร้น — อัปเกรดหรือยกเลิกได้ตลอดเวลา
            </p>
          </div>

          <div className="lp-fade lp-fade-delay-1 lp-flex-plans" style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>
            <PlanCard
              name="FREE"
              thaiName="ฟรี"
              price="฿0 / เดือน"
              color="#7a90a8"
              btnId="google-btn-free"
              features={[
                "Watchlist 3 ตัวหุ้น",
                "Top Opportunities 20 อันดับ",
                "Backtest ย้อนหลัง 1 ปี",
                "สัญญาณซื้อขายพื้นฐาน",
                "ข่าวตลาด & Sentiment",
              ]}
            />
            <PlanCard
              name="PRO"
              thaiName="โปร"
              price="ติดต่อเรา"
              color="#00d4ff"
              btnId="google-btn-pro"
              highlight
              features={[
                "Watchlist 10 ตัวหุ้น",
                "Top Opportunities 100 อันดับ",
                "Backtest ย้อนหลัง 3 ปี",
                "Fundamental Data ครบถ้วน",
                "ปฏิทินเศรษฐกิจ",
                "สัญญาณ Advanced ทั้งหมด",
              ]}
            />
            <PlanCard
              name="PREMIUM"
              thaiName="พรีเมียม"
              price="ติดต่อเรา"
              color="#e040fb"
              btnId="google-btn-premium"
              features={[
                "Watchlist 20 ตัวหุ้น",
                "Top Opportunities 500 อันดับ",
                "Backtest ย้อนหลัง 5 ปี",
                "ทุกฟีเจอร์ไม่จำกัด",
                "Line / Telegram Alerts",
                "Priority Support",
              ]}
            />
          </div>
        </div>
      </section>

      {/* ── TRUST SECTION ───────────────────────────────────────────── */}
      <section style={{ padding: "60px 0" }}>
        <div className="lp-container">
          <div className="lp-fade" style={{
            display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 24,
          }}>
            {[
              { icon: "🔒", title: "ข้อมูลปลอดภัย", desc: "Login ผ่าน Google OAuth — ไม่เก็บรหัสผ่าน" },
              { icon: "📡", title: "ข้อมูลอัปเดตทุกวัน", desc: "ราคาหุ้นและสัญญาณอัปเดตทุกวันทำการ" },
              { icon: "🏆", title: "เทคโนโลยีล้ำสมัย", desc: "Python + Django + React + AI Engine" },
              { icon: "🇹🇭", title: "สร้างโดยคนไทย", desc: "ออกแบบเพื่อนักลงทุนไทยโดยเฉพาะ" },
            ].map((t, i) => (
              <div key={i} className={`lp-fade-delay-${i + 1}`} style={{ textAlign: "center", padding: "20px 16px" }}>
                <div style={{ fontSize: 36, marginBottom: 12 }}>{t.icon}</div>
                <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 6, color: "#e2e8f0" }}>{t.title}</div>
                <div style={{ fontSize: 13, color: "#5a6e80", lineHeight: 1.6 }}>{t.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FINAL CTA ───────────────────────────────────────────────── */}
      <section style={{
        padding: "80px 24px",
        background: "linear-gradient(135deg, rgba(0,212,255,.06), rgba(224,64,251,.04))",
        borderTop: "1px solid rgba(255,255,255,.06)",
        textAlign: "center",
      }}>
        <div className="lp-fade" style={{ maxWidth: 560, margin: "0 auto" }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>◈</div>
          <h2 style={{ fontSize: 32, fontWeight: 800, margin: "0 0 16px" }}>
            เริ่มต้นวิเคราะห์หุ้นวันนี้
          </h2>
          <p style={{ fontSize: 16, color: "#6a8099", marginBottom: 36, lineHeight: 1.7 }}>
            สมัครฟรี ไม่มีค่าใช้จ่าย — เริ่มใช้งานได้ทันทีด้วย Google Account
          </p>
          {!noGoogleId && (
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 16 }}>
              <div id="google-btn-cta" />
            </div>
          )}
          <div style={{ fontSize: 12, color: "#3a4a58" }}>
            radarhoon.com — ระบบวิเคราะห์หุ้น AI-Powered
          </div>
        </div>
      </section>

      {/* ── FOOTER ──────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: "1px solid rgba(255,255,255,.05)",
        padding: "36px 24px 70px",
        background: "#050a12",
      }}>
        <div className="lp-container">
          <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 24 }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ fontSize: 22, color: "#00d4ff" }}>◈</span>
                <span style={{ fontSize: 16, fontWeight: 800 }}>Radar<span style={{ color: "#00d4ff" }}>หุ้น</span></span>
              </div>
              <div style={{ fontSize: 13, color: "#3a4a58", maxWidth: 260, lineHeight: 1.7 }}>
                ระบบวิเคราะห์หุ้น AI-Powered สำหรับนักลงทุนรายย่อยชาวไทย
              </div>
              <div style={{ marginTop: 12, fontSize: 12, color: "#2a3a4a" }}>
                radarhoon.com
              </div>
            </div>
            <div style={{ display: "flex", gap: 48, flexWrap: "wrap" }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#4a5a70", letterSpacing: 1, marginBottom: 12 }}>
                  ผลิตภัณฑ์
                </div>
                {["ฟีเจอร์", "ราคา", "Backtest", "Top Opportunities"].map(l => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: "#3a4a58", cursor: "pointer" }}>{l}</span>
                  </div>
                ))}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700, color: "#4a5a70", letterSpacing: 1, marginBottom: 12 }}>
                  ช่วยเหลือ
                </div>
                {["คำแนะนำการใช้งาน", "ถาม-ตอบ", "ติดต่อเรา", "Terms of Service"].map(l => (
                  <div key={l} style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 13, color: "#3a4a58", cursor: "pointer" }}>{l}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
          <div style={{
            marginTop: 36, paddingTop: 20,
            borderTop: "1px solid rgba(255,255,255,.04)",
            display: "flex", justifyContent: "space-between",
            flexWrap: "wrap", gap: 8,
            fontSize: 12, color: "#2a3a4a",
          }}>
            <span>© {new Date().getFullYear()} RadarHoon.com — สงวนลิขสิทธิ์</span>
            <span>⚠️ ข้อมูลบนเว็บไซต์นี้มีวัตถุประสงค์เพื่อการศึกษาเท่านั้น ไม่ใช่คำแนะนำการลงทุน</span>
          </div>
        </div>
      </footer>

      {/* ── TICKER TAPE (ดัชนีวิ่งด้านล่าง) ────────────────────────── */}
      <TickerTape />

    </div>
  )
}
