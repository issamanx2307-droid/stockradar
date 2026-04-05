import { useState, useEffect, useRef } from "react"
import { api } from "../api/client"
import { ChatMessageInfo } from "../api/types"

// ── Order Proposal ─────────────────────────────────────────────────────────
interface OrderProposal {
  order_id:    number
  symbol:      string
  side:        "buy" | "sell"
  qty:         number
  order_type:  string
  limit_price: number | null
  reasoning:   string
}

function parseOrderProposal(body: string): { text: string; proposal: OrderProposal | null } {
  const MARKER = "|||ORDER_PROPOSAL|||"
  const idx = body.indexOf(MARKER)
  if (idx === -1) return { text: body, proposal: null }
  try {
    const text     = body.slice(0, idx).trim()
    const proposal = JSON.parse(body.slice(idx + MARKER.length))
    return { text, proposal }
  } catch {
    return { text: body, proposal: null }
  }
}

function OrderConfirmCard({ proposal, onConfirm, onCancel }: {
  proposal: OrderProposal
  onConfirm: () => void
  onCancel:  () => void
}) {
  const [loading, setLoading] = useState(false)
  const [done, setDone]       = useState<"confirmed" | "cancelled" | null>(null)

  async function handleConfirm() {
    setLoading(true)
    try {
      await api.alpacaConfirmOrder(proposal.order_id)
      setDone("confirmed")
      onConfirm()
    } catch {
      alert("ส่ง order ไม่สำเร็จ กรุณาลองใหม่")
    } finally {
      setLoading(false)
    }
  }

  async function handleCancel() {
    setLoading(true)
    try {
      await api.alpacaCancelOrder(proposal.order_id)
      setDone("cancelled")
      onCancel()
    } catch {
      alert("ยกเลิก order ไม่สำเร็จ กรุณาลองใหม่")
    } finally {
      setLoading(false)
    }
  }

  const sideColor = proposal.side === "buy" ? "#2e7d32" : "#c62828"
  const sideTh    = proposal.side === "buy" ? "ซื้อ" : "ขาย"

  if (done === "confirmed") {
    return (
      <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 10, background: "rgba(46,125,50,0.1)", border: "1px solid #2e7d32", fontSize: 13 }}>
        ✅ <strong>ส่ง Order สำเร็จ</strong> — {sideTh} {proposal.qty} หุ้น {proposal.symbol} @ {proposal.order_type.toUpperCase()}
      </div>
    )
  }
  if (done === "cancelled") {
    return (
      <div style={{ marginTop: 12, padding: "10px 14px", borderRadius: 10, background: "rgba(100,100,100,0.1)", border: "1px solid #888", fontSize: 13 }}>
        ❌ <strong>ยกเลิก Order แล้ว</strong>
      </div>
    )
  }

  return (
    <div style={{
      marginTop: 12,
      padding: "14px 16px",
      borderRadius: 12,
      background: "var(--bg-card)",
      border: `2px solid ${sideColor}`,
      fontSize: 13,
    }}>
      <div style={{ fontWeight: 700, fontSize: 14, marginBottom: 8, color: sideColor }}>
        📋 AI เสนอ Order — รอการยืนยัน
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 10 }}>
        <div><strong>หุ้น:</strong> {proposal.symbol}</div>
        <div><strong>ทิศทาง:</strong> <span style={{ color: sideColor, fontWeight: 700 }}>{sideTh.toUpperCase()}</span></div>
        <div><strong>จำนวน:</strong> {proposal.qty} หุ้น</div>
        <div><strong>ประเภท:</strong> {proposal.order_type.toUpperCase()}{proposal.limit_price ? ` @ $${proposal.limit_price}` : ""}</div>
        {proposal.reasoning && (
          <div style={{ marginTop: 6, padding: "6px 10px", background: "rgba(0,0,0,0.04)", borderRadius: 6, color: "var(--text-muted)", fontSize: 12 }}>
            💡 {proposal.reasoning}
          </div>
        )}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={handleConfirm}
          disabled={loading}
          style={{
            flex: 1, padding: "8px 0", borderRadius: 8, border: "none",
            background: sideColor, color: "#fff", fontWeight: 700,
            cursor: loading ? "not-allowed" : "pointer", fontSize: 14,
          }}
        >
          {loading ? "..." : "✅ ยืนยัน"}
        </button>
        <button
          onClick={handleCancel}
          disabled={loading}
          style={{
            flex: 1, padding: "8px 0", borderRadius: 8,
            border: "1px solid var(--border)", background: "var(--bg-elevated)",
            color: "var(--text-main)", fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer", fontSize: 14,
          }}
        >
          {loading ? "..." : "❌ ยกเลิก"}
        </button>
      </div>
    </div>
  )
}

// ── Main Chat Component ────────────────────────────────────────────────────
export default function Chat({ onRead }: { onRead?: () => void }) {
  const [messages, setMessages]   = useState<ChatMessageInfo[]>([])
  const [input, setInput]         = useState("")
  const [sending, setSending]     = useState(false)
  const [loading, setLoading]     = useState(true)
  const [isAIThinking, setIsAIThinking] = useState(false)
  const bottomRef                 = useRef<HTMLDivElement>(null)
  const messagesRef               = useRef<HTMLDivElement>(null)
  const pollRef                   = useRef<ReturnType<typeof setInterval> | null>(null)
  const thinkingTimeoutRef        = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastAIMsgIdRef            = useRef<number | null>(null)
  const isThinkingRef             = useRef(false)
  const isAtBottomRef             = useRef(true)
  const prevCountRef              = useRef(0)

  function checkAtBottom() {
    const el = messagesRef.current
    if (!el) return
    // ถือว่า "อยู่ล่างสุด" ถ้าเหลือระยะ scroll น้อยกว่า 80px
    isAtBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  }

  async function loadMessages() {
    try {
      const res = await api.chatMessages()
      setMessages(res.messages)
      onRead?.()

      // ตรวจว่ามี AI message ใหม่มาหรือยัง → หยุด thinking indicator
      const latestAI = [...res.messages].reverse().find(m => m.is_ai_response)
      if (latestAI && isThinkingRef.current) {
        // หยุด thinking เมื่อ: เป็น AI msg ใหม่ (id ต่างจากที่เก็บไว้ หรือยังไม่เคยมี AI msg)
        if (lastAIMsgIdRef.current === null || latestAI.id !== lastAIMsgIdRef.current) {
          setIsAIThinking(false)
          isThinkingRef.current = false
          if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current)
        }
      }
      if (latestAI) {
        lastAIMsgIdRef.current = latestAI.id
      }
    } catch {
      /* silent */
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMessages()
    pollRef.current = setInterval(loadMessages, 6000)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current)
    }
  }, [])

  useEffect(() => {
    const newCount = messages.length
    const hadMessages = prevCountRef.current > 0
    prevCountRef.current = newCount

    // scroll ลงล่างสุดเมื่อ:
    // 1. โหลดครั้งแรก (hadMessages=false)
    // 2. user อยู่ที่ล่างสุดอยู่แล้ว (poll ดึงข้อความใหม่มา ก็ scroll ตาม)
    if (!hadMessages || isAtBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    isAtBottomRef.current = true  // ส่งข้อความแล้ว scroll ลงล่างเสมอ
    try {
      await api.chatSend(text)
      setInput("")
      // โหลด messages ใหม่ (เพื่อแสดงข้อความที่เพิ่งส่ง + อัปเดต lastAIMsgIdRef)
      // ปิด thinking ชั่วคราวเพื่อไม่ให้ loadMessages หยุด thinking ก่อนเวลา
      isThinkingRef.current = false
      await loadMessages()

      // เริ่ม thinking indicator — AI กำลังตอบอยู่
      setIsAIThinking(true)
      isThinkingRef.current = true
      if (thinkingTimeoutRef.current) clearTimeout(thinkingTimeoutRef.current)
      thinkingTimeoutRef.current = setTimeout(() => {
        setIsAIThinking(false)
        isThinkingRef.current = false
      }, 90_000)
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

  function renderLines(text: string) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {text.split("\n").map((line, i) => {
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

  function renderBody(body: string, isAI: boolean) {
    if (!isAI) return <span>{body}</span>
    const { text, proposal } = parseOrderProposal(body)
    return (
      <div>
        {renderLines(text)}
        {proposal && (
          <OrderConfirmCard
            proposal={proposal}
            onConfirm={loadMessages}
            onCancel={loadMessages}
          />
        )}
      </div>
    )
  }

  return (
    <div className="chat-outer" style={{
      width: "100%", padding: "16px 20px",
      display: "flex", flexDirection: "column", height: "calc(100vh - 56px)",
      overflow: "hidden", boxSizing: "border-box",
    }}>
      {/* Header */}
      <div className="chat-header" style={{
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
            คุยกับเอไอ
          </div>
          <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
            AI พร้อมช่วยเหลือตลอด 24 ชั่วโมง
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={messagesRef} onScroll={checkAtBottom} className="chat-messages" style={{
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
              {/* Avatar — show only for admin/team messages, not AI */}
              {!msg.is_mine && !msg.is_ai_response && (
                <div style={{
                  width: 32, height: 32, borderRadius: "50%",
                  background: "linear-gradient(135deg,#1565c0,#0288d1)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 14, flexShrink: 0,
                }}>🛠️</div>
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
        {/* AI Thinking indicator */}
        {isAIThinking && (
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8 }}>
            <img src="/ai-avatar.png" alt="AI" style={{ width: 32, height: 32, borderRadius: "50%", objectFit: "cover", border: "2px solid #1565c0", flexShrink: 0 }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 12, color: "var(--text-muted)", paddingLeft: 4, fontWeight: 600 }}>Radar AI</span>
              <div style={{
                padding: "12px 18px",
                borderRadius: "16px 16px 16px 4px",
                background: "linear-gradient(135deg,rgba(21,101,192,0.08),rgba(2,136,209,0.06))",
                border: "1px solid rgba(21,101,192,0.3)",
                display: "flex", alignItems: "center", gap: 5,
              }}>
                <span className="thinking-dot" />
                <span className="thinking-dot" />
                <span className="thinking-dot" />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input — sticks to bottom */}
      <div className="chat-input-bar" style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "10px 12px",
        background: "var(--bg-card)",
        border: "1px solid var(--border)",
        borderRadius: "0 0 12px 12px",
        borderTop: "none",
      }}>
        {/* Robot icon inside input bar */}
        <img
          src="/ai-avatar.png"
          alt="AI"
          style={{
            width: 32, height: 32, borderRadius: "50%",
            objectFit: "cover", flexShrink: 0,
            border: "2px solid #1565c0",
          }}
        />
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
            alignSelf: "stretch",
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
