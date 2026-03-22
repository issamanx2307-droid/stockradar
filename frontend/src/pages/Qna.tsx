import { useEffect, useMemo, useRef, useState } from "react"
import { api } from "../api/client"
import { StockTermInfo } from "../api/types"
import { AiTerm, TermText } from "../components/TermAssistant"

type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string; term?: StockTermInfo }

function uid() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export default function Qna() {
  const [featured, setFeatured] = useState<StockTermInfo[]>([])
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: uid(),
      role: "assistant",
      text: "พิมพ์ศัพท์เทคนิคหรือคำถาม เช่น “RSI คืออะไร”, “ทำไมต้องเลือก longterm-shortterm”",
    },
  ])
  const [busy, setBusy] = useState(false)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    api.getFeaturedTerms()
      .then(r => setFeatured(r.results || []))
      .catch(() => setFeatured([]))
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
        setMessages(prev => [
          ...prev,
          {
            id: uid(),
            role: "assistant",
            text: term.short_definition || term.full_definition || "มีคำตอบแล้ว",
            term,
          },
        ])
      } else {
        setMessages(prev => [
          ...prev,
          {
            id: uid(),
            role: "assistant",
            text: res.message || "ยังไม่มีคำตอบ ระบบได้ส่งคำถามไปให้ผู้ดูแลแล้ว",
          },
        ])
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { id: uid(), role: "assistant", text: "ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้ง" },
      ])
    } finally {
      setBusy(false)
    }
  }

  function showTerm(term: StockTermInfo) {
    setMessages(prev => [
      ...prev,
      {
        id: uid(),
        role: "assistant",
        text: term.short_definition || term.full_definition || term.term,
        term,
      },
    ])
  }

  return (
    <div className="page-body">
      <div className="page-header">
        <div className="page-title">💬 ถาม-ตอบศัพท์เทคนิค</div>
        <div className="page-subtitle">ค้นหาศัพท์/แนวทางยอดฮิต และส่งคำถามให้ผู้ดูแลเพิ่มคำตอบ</div>
      </div>

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
            <input
              className="input-field"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="พิมพ์ศัพท์หรือคำถาม แล้วกด Enter…"
              onKeyDown={e => {
                if (e.key === "Enter") send()
              }}
              disabled={busy}
            />
            <button className="btn btn-primary" onClick={send} disabled={!canSend}>
              ส่ง
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
