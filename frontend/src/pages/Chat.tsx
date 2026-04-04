import { useState, useEffect, useRef } from "react"
import { api } from "../api/client"
import { ChatMessageInfo } from "../api/types"

export default function Chat({ onRead }: { onRead?: () => void }) {
  const [messages, setMessages]   = useState<ChatMessageInfo[]>([])
  const [input, setInput]         = useState("")
  const [sending, setSending]     = useState(false)
  const [loading, setLoading]     = useState(true)
  const bottomRef                 = useRef<HTMLDivElement>(null)
  const pollRef                   = useRef<ReturnType<typeof setInterval> | null>(null)

  async function loadMessages() {
    try {
      const res = await api.chatMessages()
      setMessages(res.messages)
      onRead?.()
    } catch {
      /* silent */
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMessages()
    pollRef.current = setInterval(loadMessages, 6000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await api.chatSend(text)
      setInput("")
      await loadMessages()
    } catch {
      /* silent */
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function formatTime(iso: string) {
    const d = new Date(iso)
    return d.toLocaleString("th-TH", {
      day: "2-digit", month: "short",
      hour: "2-digit", minute: "2-digit",
    })
  }

  function renderBody(body: string, isAI: boolean) {
    if (!isAI) return <span>{body}</span>
    // แปลง **bold** → <strong> แล้ว render แต่ละบรรทัดแยกกัน
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {body.split("\n").map((line, i) => {
          const parts = line.split(/(\*\*[^*]+\*\*)/g)
          return (
            <div key={i} style={{ minHeight: line.trim() === "" ? 6 : undefined }}>
              {parts.map((p, j) =>
                p.startsWith("**") && p.endsWith("**")
                  ? <strong key={j}>{p.slice(2, -2)}</strong>
                  : <span key={j}>{p}</span>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div style={{
      width: "100%", padding: "16px 20px",
      display: "flex", flexDirection: "column", height: "calc(100vh - 120px)",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "12px 16px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "12px 12px 0 0",
        borderBottom: "none",
      }}>
        <img src="/ai-avatar.png" alt="Radar AI" style={{ width: 38, height: 38, borderRadius: "50%", objectFit: "cover", border: "2px solid #1565c0" }} />
        <div>
          <div style={{ fontWeight: 700, fontSize: 15, color: "var(--text-main)" }}>
            ติดต่อทีมงาน
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            แอดมินจะตอบกลับโดยเร็วที่สุด
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: "16px",
        background: "var(--bg-elevated)",
        border: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        gap: 12,
        minHeight: 0,
      }}>
        {loading ? (
          <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: 40 }}>
            <div className="loading-spinner" style={{ margin: "0 auto 8px" }} />
            กำลังโหลด...
          </div>
        ) : messages.length === 0 ? (
          <div style={{
            textAlign: "center", color: "var(--text-muted)",
            marginTop: 60, fontSize: 14,
          }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>💬</div>
            <div>ยังไม่มีการสนทนา</div>
            <div style={{ fontSize: 12, marginTop: 4 }}>พิมพ์ข้อความเพื่อเริ่มต้น</div>
          </div>
        ) : (
          messages.map(msg => (
            <div key={msg.id} style={{
              display: "flex",
              flexDirection: msg.is_mine ? "row-reverse" : "row",
              alignItems: "flex-end",
              gap: 8,
            }}>
              {/* Avatar */}
              {!msg.is_mine && (
                msg.is_ai_response ? (
                  <img
                    src="/ai-avatar.png"
                    alt="AI"
                    style={{
                      width: 36, height: 36, borderRadius: "50%",
                      objectFit: "cover", flexShrink: 0,
                      border: "2px solid #1565c0",
                      background: "#0d1b2a",
                    }}
                  />
                ) : (
                  <div style={{
                    width: 32, height: 32, borderRadius: "50%",
                    background: "linear-gradient(135deg,#1565c0,#0288d1)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 14, flexShrink: 0,
                  }}>🛠️</div>
                )
              )}

              {/* Bubble */}
              <div style={{
                maxWidth: msg.is_ai_response ? "88%" : "72%",
                display: "flex", flexDirection: "column",
                alignItems: msg.is_mine ? "flex-end" : "flex-start", gap: 4,
              }}>
                {!msg.is_mine && (
                  <span style={{ fontSize: 12, color: "var(--text-muted)", paddingLeft: 4, fontWeight: 600 }}>
                    {msg.is_ai_response ? "Radar AI" : "ทีมงาน"}
                  </span>
                )}
                <div style={{
                  padding: "12px 16px",
                  borderRadius: msg.is_mine
                    ? "16px 16px 4px 16px"
                    : "16px 16px 16px 4px",
                  background: msg.is_mine
                    ? "linear-gradient(135deg,#1565c0,#0288d1)"
                    : msg.is_ai_response
                      ? "linear-gradient(135deg,rgba(21,101,192,0.08),rgba(2,136,209,0.06))"
                      : "var(--bg-card)",
                  border: msg.is_mine ? "none" : msg.is_ai_response
                    ? "1px solid rgba(21,101,192,0.3)"
                    : "1px solid var(--border)",
                  color: msg.is_mine ? "#fff" : "var(--text-main)",
                  fontSize: 15,
                  lineHeight: 1.7,
                  wordBreak: "break-word",
                  boxShadow: "0 1px 4px rgba(0,0,0,.2)",
                }}>
                  {renderBody(msg.body, !!msg.is_ai_response)}
                </div>
                <span style={{ fontSize: 10, color: "var(--text-muted)", paddingLeft: 2, paddingRight: 2 }}>
                  {formatTime(msg.created_at)}
                  {msg.is_mine && (
                    <span style={{ marginLeft: 4, color: msg.is_read ? "#4caf50" : "var(--text-muted)" }}>
                      {msg.is_read ? "✓✓" : "✓"}
                    </span>
                  )}
                </span>
              </div>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        display: "flex", gap: 8,
        padding: "12px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "0 0 12px 12px",
        borderTop: "none",
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="พิมพ์ข้อความ... (Enter เพื่อส่ง, Shift+Enter ขึ้นบรรทัดใหม่)"
          rows={2}
          style={{
            flex: 1,
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "10px 12px",
            color: "var(--text-main)",
            fontSize: 14,
            resize: "none",
            lineHeight: 1.5,
            outline: "none",
            fontFamily: "inherit",
          }}
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || sending}
          style={{
            padding: "0 20px",
            background: input.trim() && !sending
              ? "linear-gradient(135deg,#1565c0,#0288d1)"
              : "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            color: input.trim() && !sending ? "#fff" : "var(--text-muted)",
            cursor: input.trim() && !sending ? "pointer" : "not-allowed",
            fontSize: 18,
            transition: "all .2s",
            flexShrink: 0,
          }}
        >
          {sending ? "..." : "➤"}
        </button>
      </div>
    </div>
  )
}
