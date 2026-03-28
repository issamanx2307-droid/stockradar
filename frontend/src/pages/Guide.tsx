import { useEffect, useMemo, useRef, useState } from "react"
import { GUIDE_DATA, GuideItem } from "../data/guideData"
import { api } from "../api/client"
import { StockTermInfo } from "../api/types"
import { AiTerm, TermText } from "../components/TermAssistant"

// ── Tab button style ──────────────────────────────────────────────────────────
function tabStyle(active: boolean) {
  return {
    padding: "8px 18px", borderRadius: 8, fontSize: 13, fontWeight: 700, cursor: "pointer",
    border: `1.5px solid ${active ? "var(--accent)" : "var(--border)"}`,
    background: active ? "var(--accent-dim)" : "transparent",
    color: active ? "var(--accent)" : "var(--text-muted)",
    transition: "all 0.15s",
  } as React.CSSProperties
}

// ── Q&A Tab ───────────────────────────────────────────────────────────────────
type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string; term?: StockTermInfo }

function uid() { return `${Date.now()}-${Math.random().toString(16).slice(2)}` }

function QnaTab() {
  const [featured, setFeatured] = useState<StockTermInfo[]>([])
  const [query, setQuery]       = useState("")
  const [messages, setMessages] = useState<Msg[]>([{
    id: uid(), role: "assistant",
    text: "พิมพ์ศัพท์เทคนิคหรือคำถาม เช่น RSI คืออะไร, BB Bands ใช้ยังไง",
  }])
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    api.getFeaturedTerms().then(r => setFeatured(r.results || [])).catch(() => setFeatured([]))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length])

  const canSend = useMemo(() => query.trim().length > 0 && !busy, [query, busy])

  async function send() {
    const text = query.trim()
    if (!text || busy) return
    setQuery("")
    setBusy(true)
    setMessages(prev => [...prev, { id: uid(), role: "user", text }])
    try {
      const res = await api.askQuestion(text)
      if (res.found && res.term) {
        const term = res.term
        setMessages(prev => [...prev, {
          id: uid(), role: "assistant",
          text: term.short_definition || term.full_definition || "มีคำตอบแล้ว",
          term,
        }])
      } else {
        setMessages(prev => [...prev, {
          id: uid(), role: "assistant",
          text: res.message || "ยังไม่มีคำตอบ ระบบได้ส่งคำถามไปให้ผู้ดูแลแล้ว",
        }])
      }
    } catch {
      setMessages(prev => [...prev, { id: uid(), role: "assistant", text: "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง" }])
    } finally { setBusy(false) }
  }

  function showTerm(term: StockTermInfo) {
    setMessages(prev => [...prev, {
      id: uid(), role: "assistant",
      text: term.short_definition || term.full_definition || term.term,
      term,
    }])
  }

  return (
    <div className="qna-layout">
      <aside className="card qna-side">
        <div className="card-title">คำถาม/ศัพท์ที่พบบ่อย</div>
        <div className="qna-term-list">
          {featured.map(t => (
            <button key={t.term} className="qna-term-btn" onClick={() => showTerm(t)}>
              <div className="qna-term-code"><AiTerm token={t.term}>{t.term}</AiTerm></div>
              <div className="qna-term-desc"><TermText text={t.short_definition} /></div>
            </button>
          ))}
        </div>
      </aside>

      <section className="card qna-main">
        <div className="qna-messages">
          {messages.map(m => (
            <div key={m.id} className={`qna-msg ${m.role}`}>
              <div className="qna-bubble">
                <div className="qna-text"><TermText text={m.text} /></div>
                {"term" in m && m.term && (
                  <div className="qna-term-full">
                    <div className="qna-term-full-title"><AiTerm token={m.term.term}>{m.term.term}</AiTerm></div>
                    <div className="qna-term-full-body">{m.term.full_definition}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="qna-input">
          <input className="input-field" value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="พิมพ์ศัพท์หรือคำถาม แล้วกด Enter…"
            onKeyDown={e => { if (e.key === "Enter") send() }}
            disabled={busy} />
          <button className="btn btn-primary" onClick={send} disabled={!canSend}>ส่ง</button>
        </div>
      </section>
    </div>
  )
}

// ── Guide Tab ─────────────────────────────────────────────────────────────────
function GuideTab() {
  const [selected, setSelected] = useState<GuideItem>(GUIDE_DATA[0])

  return (
    <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 16, alignItems: "start" }}>
      {/* Sidebar list */}
      <div className="card" style={{ padding: "12px 8px" }}>
        <div className="card-title" style={{ paddingLeft: 8 }}>รายชื่อเครื่องมือ</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {GUIDE_DATA.map(item => (
            <button key={item.id}
              className={`nav-btn ${selected.id === item.id ? "active" : ""}`}
              onClick={() => setSelected(item)}
              style={{ textAlign: "left" }}>
              <span style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontWeight: 700 }}>{item.id.toUpperCase()}</span>
                <small style={{ fontSize: 10, opacity: 0.6 }}>{item.category}</small>
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      <div className="card" style={{ padding: "24px 28px" }}>
        <div style={{ marginBottom: 20 }}>
          <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
            background: "var(--accent-dim)", color: "var(--accent)", marginBottom: 8, display: "inline-block" }}>
            {selected.category}
          </span>
          <div style={{ fontSize: 22, fontWeight: 800, color: "var(--accent)", marginTop: 4 }}>{selected.name}</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase",
              letterSpacing: "0.08em", marginBottom: 8 }}>คำอธิบาย</div>
            <p style={{ fontSize: 15, lineHeight: 1.7, color: "var(--text-primary)", margin: 0 }}>
              {selected.description}
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ padding: "14px 16px", background: "var(--bg-elevated)",
              borderRadius: 8, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>สูตรการคำนวณ</div>
              <code style={{ color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: 13 }}>
                {selected.formula}
              </code>
            </div>
            <div style={{ padding: "14px 16px", background: "var(--bg-elevated)",
              borderRadius: 8, border: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>ค่าที่แนะนำ</div>
              <span style={{ color: "#ffd740", fontWeight: 700, fontSize: 14 }}>{selected.recommended_value}</span>
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)",
              textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 10 }}>ความหมายของสัญญาณ</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <div style={{ padding: "14px 16px", borderLeft: "4px solid var(--green)",
                background: "rgba(0,230,118,0.06)", borderRadius: "0 8px 8px 0" }}>
                <div style={{ color: "var(--green)", fontWeight: 700, marginBottom: 6 }}>🟢 Bullish (ขาขึ้น)</div>
                <p style={{ fontSize: 13, margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                  {selected.signal_meaning.bullish}
                </p>
              </div>
              <div style={{ padding: "14px 16px", borderLeft: "4px solid var(--red)",
                background: "rgba(255,82,82,0.06)", borderRadius: "0 8px 8px 0" }}>
                <div style={{ color: "var(--red)", fontWeight: 700, marginBottom: 6 }}>🔴 Bearish (ขาลง)</div>
                <p style={{ fontSize: 13, margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                  {selected.signal_meaning.bearish}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Combined Page ────────────────────────────────────────────────────────
export default function Guide() {
  const [tab, setTab] = useState<"guide" | "qna">("guide")

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">💡 คำแนะนำ & ถาม-ตอบ</div>
        <div className="page-subtitle">คู่มือ Indicator · สูตรคำนวณ · ถาม-ตอบศัพท์เทคนิค</div>
      </div>
      <div className="page-body">

        {/* Tab nav */}
        <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
          <button style={tabStyle(tab === "guide")} onClick={() => setTab("guide")}>
            💡 คำแนะนำ Indicator
          </button>
          <button style={tabStyle(tab === "qna")} onClick={() => setTab("qna")}>
            💬 ถาม-ตอบศัพท์เทคนิค
          </button>
        </div>

        {tab === "guide" && <GuideTab />}
        {tab === "qna"   && <QnaTab />}

      </div>
    </div>
  )
}
