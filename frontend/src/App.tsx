import { useState, useRef } from "react"
import { useRadarWS } from "./hooks/useRadarWS"
import { WsStatus } from "./components/WsStatus"
import { ScannerProgress } from "./components/ScannerProgress"
import Dashboard from "./pages/Dashboard"
import Scanner from "./pages/Scanner"
import Chart from "./pages/Chart"
import StrategyBuilder from "./pages/StrategyBuilder"
import Profile from "./pages/Profile"
import Contact from "./pages/Contact"
import Guide from "./pages/Guide"
import Qna from "./pages/Qna"
import News from "./pages/News"
import Analyze from "./pages/Analyze"
import EngineScan from "./pages/EngineScan"
import Portfolio from "./pages/Portfolio"
import EngineBacktest from "./pages/EngineBacktest"
import Watchlist from "./pages/Watchlist"
import Fundamental from "./pages/Fundamental"
import EconomicCalendar from "./pages/EconomicCalendar"
import { AutoTermHighlight, TermAssistantProvider, TermAssistantToggle } from "./components/TermAssistant"
import TickerTape from "./components/TickerTape"
import "./App.css"

const NAV_ITEMS = [
  { id:"dashboard",   label:"ราดาร์",           icon:"📡" },
  { id:"engine_scan", label:"Top Opportunities",  icon:"🔥" },
  { id:"watchlist",   label:"Watchlist",           icon:"⭐" },
  { id:"news",        label:"ข่าว & Sentiment",   icon:"📰" },
  { id:"analyze",     label:"วิเคราะห์หุ้น",     icon:"🔬" },
  { id:"fundamental", label:"Fundamental",         icon:"📊" },
  { id:"portfolio",   label:"Portfolio",           icon:"💼" },
  { id:"scanner",     label:"สแกนหุ้น",           icon:"🔍" },
  { id:"chart",       label:"กราฟ",               icon:"📈" },
  { id:"calendar",    label:"ปฏิทินเศรษฐกิจ",     icon:"📅" },
  { id:"strategy",    label:"กลยุทธ์",             icon:"🎯" },
  { id:"backtest",    label:"Backtest",            icon:"⏪" },
  { id:"guide",       label:"คำแนะนำ",            icon:"💡" },
  { id:"qna",         label:"ถาม-ตอบ",            icon:"💬" },
  { id:"profile",     label:"โปรไฟล์",            icon:"👤" },
  { id:"contact",     label:"ติดต่อเรา",          icon:"📞" },
]

export default function App() {
  const [page, setPage] = useState("dashboard")
  const [history, setHistory] = useState<string[]>([])
  const [chartSymbol, setChartSymbol] = useState<string | null>(null)
  const [analyzeSymbol, setAnalyzeSymbol] = useState<string | null>(null)
  const ws = useRadarWS()

  function navigateTo(newPage: string) {
    if (newPage !== page) { setHistory([]); setPage(newPage) }
  }

  function goBack() {
    if (history.length > 0) {
      const prev = history[history.length - 1]
      setHistory(h => h.slice(0, -1))
      setPage(prev)
    }
  }

  function openChart(symbol: string) {
    setChartSymbol(symbol)
    setHistory(h => [...h, page])
    setPage("chart")
  }

  function openAnalyze(symbol: string) {
    setAnalyzeSymbol(symbol)
    setHistory(h => [...h, page])
    setPage("analyze")
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
            {NAV_ITEMS.map(item => (
              <button key={item.id}
                className={`nav-btn ${page === item.id ? "active" : ""}`}
                onClick={() => navigateTo(item.id)}>
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="sidebar-footer">
            <span className="version-badge">v5.1</span>
            <div style={{ marginTop:10 }}><TermAssistantToggle /></div>
          </div>
        </aside>

        <main className="main-content" style={{ paddingBottom:34 }}>
          {history.length > 0 && (
            <div className="back-btn-container">
              <button className="back-btn" onClick={goBack}>
                <span className="back-icon">←</span> ย้อนกลับ
              </button>
            </div>
          )}
          <AutoTermHighlight>
            {page === "dashboard"   && <Dashboard ws={ws} onOpenChart={openChart} />}
            {page === "engine_scan" && <EngineScan onOpenChart={openChart} />}
            {page === "watchlist"   && <Watchlist onOpenChart={openChart} />}
            {page === "news"        && <News onOpenChart={openChart} />}
            {page === "analyze"     && <Analyze onOpenChart={openChart} initialSymbol={analyzeSymbol} />}
            {page === "fundamental" && <Fundamental onOpenChart={openChart} />}
            {page === "portfolio"   && <Portfolio onOpenChart={openChart} />}
            {page === "scanner"     && <Scanner onOpenChart={openChart} onAnalyze={openAnalyze} />}
            {page === "chart"       && <Chart symbol={chartSymbol} />}
            {page === "calendar"    && <EconomicCalendar />}
            {page === "strategy"    && <StrategyBuilder />}
            {page === "backtest"    && <EngineBacktest onOpenChart={openChart} />}
            {page === "guide"       && <Guide />}
            {page === "qna"         && <Qna />}
            {page === "profile"     && <Profile />}
            {page === "contact"     && <Contact />}
          </AutoTermHighlight>
        </main>
      </div>
      <TickerTape />
    </TermAssistantProvider>
  )
}
