import { useState, useRef, useEffect } from "react"
import { useRadarWS } from "./hooks/useRadarWS"
import { WsStatus } from "./components/WsStatus"
import { ScannerProgress } from "./components/ScannerProgress"
import { AuthProvider, useAuth } from "./context/AuthContext"
import LandingPage from "./pages/LandingPage"
import UserBadge from "./components/UserBadge"
import Dashboard from "./pages/Dashboard"
import Scanner from "./pages/Scanner"
import Chart from "./pages/Chart"
import StrategyBuilder from "./pages/StrategyBuilder"
import Profile from "./pages/Profile"
import Contact from "./pages/Contact"
import Guide from "./pages/Guide"
import News from "./pages/News"
import Analyze from "./pages/Analyze"
import EngineScan from "./pages/EngineScan"
import Portfolio from "./pages/Portfolio"
import EngineBacktest from "./pages/EngineBacktest"
import Watchlist from "./pages/Watchlist"
import Fundamental from "./pages/Fundamental"
import VIScreen from "./pages/VIScreen"
import Chat from "./pages/Chat"
import { AutoTermHighlight, TermAssistantProvider, TermAssistantToggle } from "./components/TermAssistant"
import TickerTape from "./components/TickerTape"
import "./App.css"

// ── เมนูสำหรับ User ทั่วไป ───────────────────────────────────────────────────
const USER_NAV: { id: string; label: string; icon: string }[] = [
  { id: "dashboard",    label: "ราดาร์",            icon: "📡" },
  { id: "engine_scan",  label: "Top Opportunities",  icon: "🔥" },
  { id: "watchlist",    label: "Watchlist",           icon: "⭐" },
  { id: "news",         label: "ข่าว & Sentiment",   icon: "📰" },
  { id: "analyze",      label: "วิเคราะห์หุ้น",     icon: "🔬" },
  { id: "fundamental",  label: "Fundamental",         icon: "📊" },
  { id: "vi_screen",    label: "หุ้น VI",              icon: "💎" },
  { id: "portfolio",    label: "Portfolio",           icon: "💼" },
  { id: "scanner",      label: "สแกนหุ้น",           icon: "🔍" },
  { id: "chart",        label: "กราฟ",               icon: "📈" },
  { id: "strategy",     label: "กลยุทธ์",             icon: "🎯" },
  { id: "backtest",     label: "Backtest",            icon: "⏪" },
  { id: "guide",        label: "คำแนะนำ & ถาม-ตอบ",  icon: "💡" },
  { id: "profile",      label: "บัญชี & สมาชิก",     icon: "⚙️" },
  { id: "contact",      label: "ติดต่อเรา",          icon: "📞" },
  { id: "chat",         label: "ข้อความ",             icon: "💬" },
]

function AppInner() {
  const { user, loading } = useAuth()
  const isAdmin = user?.is_staff || user?.is_superuser

  // ── hash-based navigation (persist page on refresh) ──────────────────────
  const VALID_PAGES = [
    "dashboard","engine_scan","watchlist","news","analyze","fundamental",
    "vi_screen","scanner","chart","strategy","backtest",
    "guide","profile","contact","subscription","chat",
  ]
  function getHashPage(fallback: string) {
    const h = window.location.hash.replace("#", "")
    return VALID_PAGES.includes(h) ? h : fallback
  }

  const [page, setPage] = useState(() => getHashPage("dashboard"))
  const [history, setHistory] = useState<string[]>([])
  const [chartSymbol, setChartSymbol]     = useState<string | null>(null)
  const [analyzeSymbol, setAnalyzeSymbol] = useState<string | null>(null)
  const [chatUnread, setChatUnread]       = useState(0)
  const ws = useRadarWS()

  // ── Poll unread chat count (user only) ───────────────────────────────────
  useEffect(() => {
    if (!user || isAdmin) return
    async function pollUnread() {
      try {
        const res = await (await import("./api/client")).api.chatMessages()
        const unread = res.messages.filter((m: any) => !m.is_mine && !m.is_read).length
        setChatUnread(unread)
      } catch {/* silent */}
    }
    pollUnread()
    const iv = setInterval(pollUnread, 15000)
    return () => clearInterval(iv)
  }, [user, isAdmin])

  // sync hash → state (browser back/forward)
  useEffect(() => {
    function onHashChange() {
      const h = getHashPage("dashboard")
      setPage(h); setHistory([])
    }
    window.addEventListener("hashchange", onHashChange)
    return () => window.removeEventListener("hashchange", onHashChange)
  }, [])

  function navigateTo(id: string) {
    if (id !== page) {
      setHistory([])
      setPage(id)
      window.location.hash = id
    }
  }
  function goBack() {
    if (history.length > 0) {
      const prev = history[history.length - 1]
      setHistory(h => h.slice(0, -1))
      setPage(prev)
      window.location.hash = prev
    }
  }
  function openChart(symbol: string) {
    setChartSymbol(symbol); setHistory(h => [...h, page]); setPage("chart")
    window.location.hash = "chart"
  }
  function openAnalyze(symbol: string) {
    setAnalyzeSymbol(symbol); setHistory(h => [...h, page]); setPage("analyze")
    window.location.hash = "analyze"
  }

  useEffect(() => {
    if (!loading && user && page === "portfolio" && !user.can_use_portfolio) {
      navigateTo("dashboard")
    }
  }, [user, loading])

  if (loading) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: "var(--bg-main,#0a1929)", flexDirection: "column", gap: 16 }}>
        <div style={{ fontSize: 40 }}>◈</div>
        <div className="loading-spinner" />
        <div style={{ color: "var(--text-muted)", fontSize: 13 }}>กำลังโหลด...</div>
      </div>
    )
  }

  if (!user) return <LandingPage />

  // ── Admin → redirect to Django admin ────────────────────────────────────
  if (isAdmin) {
    return (
      <div style={{
        height: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: "var(--bg-main,#0a1929)",
        flexDirection: "column", gap: 20,
      }}>
        <div style={{ fontSize: 48 }}>🛠️</div>
        <div style={{ color: "var(--text-main)", fontSize: 18, fontWeight: 700 }}>
          สวัสดี {user.first_name || user.username}
        </div>
        <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
          บัญชีนี้เป็น Admin — กรุณาใช้หน้าจัดการระบบ
        </div>
        <a
          href="/admin/"
          style={{
            padding: "12px 32px",
            background: "linear-gradient(135deg,#1565c0,#0288d1)",
            color: "#fff", borderRadius: 8, textDecoration: "none",
            fontSize: 15, fontWeight: 700, letterSpacing: 0.5,
          }}
        >
          เข้า Django Admin →
        </a>
      </div>
    )
  }

  return (
    <TermAssistantProvider>
      <div className="app">
        <WsStatus connected={ws.connected} />
        <ScannerProgress progress={ws.scanProgress} done={ws.scanDone} />

        <aside className="sidebar">
          <div className="sidebar-logo">
            <span className="logo-icon">◈</span>
            <span className="logo-text">Radar<br /><small>หุ้น</small></span>
          </div>
          <nav className="sidebar-nav">
            {USER_NAV.filter(item => {
              if (item.id === "portfolio") return !!(user?.can_use_portfolio)
              return true
            }).map(item => (
              <button key={item.id}
                className={`nav-btn ${page === item.id ? "active" : ""}`}
                onClick={() => navigateTo(item.id)}>
                <span className="nav-icon" style={{ position: "relative" }}>
                  {item.icon}
                  {item.id === "chat" && chatUnread > 0 && (
                    <span style={{
                      position: "absolute", top: -4, right: -6,
                      background: "#f44336", color: "#fff",
                      fontSize: 9, fontWeight: 800,
                      borderRadius: 10, padding: "0 4px",
                      minWidth: 14, textAlign: "center",
                      lineHeight: "14px",
                    }}>{chatUnread > 9 ? "9+" : chatUnread}</span>
                  )}
                </span>
                <span className="nav-label">{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="sidebar-footer">
            <UserBadge onSubscription={() => navigateTo("subscription")} />
            <span className="version-badge">v5.1</span>
            <div style={{ marginTop: 8 }}><TermAssistantToggle /></div>
          </div>
        </aside>

        <main className="main-content" style={{ paddingBottom: 34 }}>
          {history.length > 0 && (
            <div className="back-btn-container">
              <button className="back-btn" onClick={goBack}>
                <span className="back-icon">←</span> ย้อนกลับ
              </button>
            </div>
          )}
          {/* ── Legal Disclaimer (ก.ล.ต.) ── */}
          <div style={{
            margin: "12px 16px 0",
            padding: "8px 14px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderLeft: "3px solid var(--yellow)",
            borderRadius: 6,
            fontSize: 11,
            color: "var(--text-muted)",
            lineHeight: 1.7,
          }}>
            <span style={{ fontWeight: 700, color: "#FFD700" }}>⚠️ คำเตือน: </span>
            <span style={{ fontWeight: 700, color: "#FFD700" }}>
              แพลตฟอร์มนี้เป็นเครื่องมือวิเคราะห์ข้อมูลเชิงสถิติ แบบที่เผยแพร่ทั่วไป
              ไม่ถือเป็นคำแนะนำการลงทุน การซื้อขายหลักทรัพย์มีความเสี่ยง
              ผู้ใช้งานควรศึกษาข้อมูลและตัดสินใจด้วยตนเอง
            </span>
          </div>

          <AutoTermHighlight>
            {page === "dashboard"    && <Dashboard ws={ws} onOpenChart={openChart} />}
            {page === "engine_scan"  && <EngineScan onOpenChart={openChart} />}
            {page === "watchlist"    && <Watchlist onOpenChart={openChart} />}
            {page === "news"         && <News onOpenChart={openChart} />}
            {page === "analyze"      && <Analyze onOpenChart={openChart} initialSymbol={analyzeSymbol} />}
            {page === "fundamental"  && <Fundamental onOpenChart={openChart} />}
            {page === "vi_screen"    && <VIScreen onOpenChart={openChart} />}
            {page === "portfolio"    && user?.can_use_portfolio && <Portfolio onOpenChart={openChart} />}
            {page === "scanner"      && <Scanner onOpenChart={openChart} onAnalyze={openAnalyze} />}
            {page === "chart"        && <Chart symbol={chartSymbol} />}
            {page === "strategy"     && <StrategyBuilder />}
            {page === "backtest"     && <EngineBacktest onOpenChart={openChart} />}
            {page === "guide"        && <Guide />}
            {page === "profile"      && <Profile />}
            {page === "contact"      && <Contact />}
            {page === "chat"         && <Chat onRead={() => setChatUnread(0)} />}
          </AutoTermHighlight>
        </main>
      </div>
      <TickerTape />
    </TermAssistantProvider>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppInner />
    </AuthProvider>
  )
}
