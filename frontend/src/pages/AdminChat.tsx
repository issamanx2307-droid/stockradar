import { useState, useEffect, useRef } from "react"
import { api } from "../api/client"
import { ChatConversation, ChatMessageInfo } from "../api/types"

// ── Blinking dot component ──────────────────────────────────────────────────
function BlinkDot() {
  return (
    <span style={{
      display: "inline-block",
      width: 8, height: 8,
      borderRadius: "50%",
      background: "#f44336",
      animation: "chatBlink 1s infinite",
      flexShrink: 0,
    }} />
  )
}

// ── Single conversation card ─────────────────────────────────────────────────
function ConvCard({
  conv,
  onDismiss,
}: {
  conv: ChatConversation
  onDismiss: (id: number) => void
}) {
  const [expanded, setExpanded]   = useState(false)
  const [messages, setMessages]   = useState<ChatMessageInfo[]>([])
  const [input, setInput]         = useState("")
  const [sending, setSending]     = useState(false)
  const [loading, setLoading]     = useState(false)
  const [localUnread, setLocalUnread] = useState(conv.unread)
  const bottomRef                 = useRef<HTMLDivElement>(null)

  async function loadMessages() {
    setLoading(true)
    try {
      const res = await api.chatMessages(conv.user_id)
      setMessages(res.messages)
      setLocalUnread(0)
    } catch {/* silent */}
    finally { setLoading(false) }
  }

  function handleExpand() {
    if (!expanded) {
      setExpanded(true)
      loadMessages()
    } else {
      setExpanded(false)
    }
  }

  useEffect(() => {
    if (expanded) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, expanded])

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setSending(true)
    try {
      await api.chatSend(text, conv.user_id)
      setInput("")
      await loadMessages()
    } catch {/* silent */}
    finally { setSending(false) }
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

  const displayName = conv.first_name
    ? `${conv.first_name} ${conv.last_name}`.trim()
    : conv.username

  return (
    <div style={{
      background: "var(--bg-card)",
      border: `1px solid ${localUnread > 0 ? "rgba(244,67,54,.5)" : "var(--border)"}`,
      borderRadius: 10,
      overflow: "hidden",
      transition: "border-color .3s",
      boxShadow: localUnread > 0 ? "0 0 12px rgba(244,67,54,.15)" : "none",
    }}>
      {/* Card header */}
      <div
        onClick={handleExpand}
        style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "12px 14px",
          cursor: "pointer",
          userSelect: "none",
        }}
      >
        {/* Avatar */}
        <div style={{
          width: 38, height: 38, borderRadius: "50%",
          background: "linear-gradient(135deg,#1565c0,#0288d1)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, flexShrink: 0, fontWeight: 700,
          color: "#fff",
        }}>
          {displayName.charAt(0).toUpperCase()}
        </div>

        {/* Info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontWeight: 600, fontSize: 14, color: "var(--text-main)" }}>
              {displayName}
            </span>
            {localUnread > 0 && <BlinkDot />}
            {localUnread > 0 && (
              <span style={{
                background: "#f44336", color: "#fff",
                fontSize: 10, fontWeight: 700,
                borderRadius: 10, padding: "1px 6px",
              }}>
                {localUnread} ใหม่
              </span>
            )}
          </div>
          <div style={{
            fontSize: 12, color: "var(--text-muted)",
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            @{conv.username} · {conv.email}
          </div>
          {conv.last_body && (
            <div style={{
              fontSize: 12, color: "var(--text-secondary)",
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              marginTop: 2,
            }}>
              {conv.last_body}
            </div>
          )}
        </div>

        {/* Right side */}
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
          {conv.last_at && (
            <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
              {formatTime(conv.last_at)}
            </span>
          )}
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {expanded ? "▲" : "▼"}
          </span>
        </div>

        {/* X dismiss */}
        <button
          onClick={e => { e.stopPropagation(); onDismiss(conv.user_id) }}
          title="ปิด"
          style={{
            width: 24, height: 24, borderRadius: "50%",
            background: "rgba(255,255,255,.08)",
            border: "none", cursor: "pointer",
            color: "var(--text-muted)", fontSize: 12,
            display: "flex", alignItems: "center", justifyContent: "center",
            flexShrink: 0, marginLeft: 2,
            transition: "background .15s",
          }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(244,67,54,.3)")}
          onMouseLeave={e => (e.currentTarget.style.background = "rgba(255,255,255,.08)")}
        >✕</button>
      </div>

      {/* Expanded chat area */}
      {expanded && (
        <div style={{ borderTop: "1px solid var(--border)" }}>
          {/* Messages */}
          <div style={{
            height: 280, overflowY: "auto",
            padding: "12px 14px",
            display: "flex", flexDirection: "column", gap: 10,
            background: "var(--bg-elevated)",
          }}>
            {loading ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", paddingTop: 30 }}>
                <div className="loading-spinner" style={{ margin: "0 auto 6px" }} />
                กำลังโหลด...
              </div>
            ) : messages.length === 0 ? (
              <div style={{ textAlign: "center", color: "var(--text-muted)", paddingTop: 30, fontSize: 13 }}>
                ยังไม่มีข้อความ
              </div>
            ) : (
              messages.map(msg => (
                <div key={msg.id} style={{
                  display: "flex",
                  flexDirection: msg.is_admin_msg ? "row-reverse" : "row",
                  alignItems: "flex-end",
                  gap: 6,
                }}>
                  <div style={{
                    maxWidth: "72%",
                    display: "flex", flexDirection: "column",
                    alignItems: msg.is_admin_msg ? "flex-end" : "flex-start",
                    gap: 2,
                  }}>
                    <div style={{
                      padding: "8px 12px",
                      borderRadius: msg.is_admin_msg
                        ? "12px 12px 4px 12px"
                        : "12px 12px 12px 4px",
                      background: msg.is_admin_msg
                        ? "linear-gradient(135deg,#1565c0,#0288d1)"
                        : "var(--bg-card)",
                      border: msg.is_admin_msg ? "none" : "1px solid var(--border)",
                      color: msg.is_admin_msg ? "#fff" : "var(--text-main)",
                      fontSize: 13,
                      lineHeight: 1.5,
                      wordBreak: "break-word",
                    }}>
                      {msg.body}
                    </div>
                    <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                      {formatTime(msg.created_at)}
                    </span>
                  </div>
                </div>
              ))
            )}
            <div ref={bottomRef} />
          </div>

          {/* Reply input */}
          <div style={{
            display: "flex", gap: 8,
            padding: "10px 14px",
            background: "var(--bg-card)",
            borderTop: "1px solid var(--border)",
          }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`ตอบกลับ ${displayName}... (Enter เพื่อส่ง)`}
              rows={2}
              style={{
                flex: 1,
                background: "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "8px 10px",
                color: "var(--text-main)",
                fontSize: 13,
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
                padding: "0 16px",
                background: input.trim() && !sending
                  ? "linear-gradient(135deg,#1565c0,#0288d1)"
                  : "var(--bg-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: input.trim() && !sending ? "#fff" : "var(--text-muted)",
                cursor: input.trim() && !sending ? "pointer" : "not-allowed",
                fontSize: 16,
                flexShrink: 0,
              }}
            >
              {sending ? "..." : "➤"}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}


// ── Main AdminChat page ──────────────────────────────────────────────────────
export default function AdminChat() {
  const [convs, setConvs]         = useState<ChatConversation[]>([])
  const [dismissed, setDismissed] = useState<Set<number>>(new Set())
  const [loading, setLoading]     = useState(true)
  const pollRef                   = useRef<ReturnType<typeof setInterval> | null>(null)

  async function loadConvs() {
    try {
      const res = await api.chatConversations()
      setConvs(res.conversations)
    } catch {/* silent */}
    finally { setLoading(false) }
  }

  useEffect(() => {
    loadConvs()
    pollRef.current = setInterval(loadConvs, 8000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  function handleDismiss(userId: number) {
    setDismissed(prev => new Set(prev).add(userId))
  }

  const visible = convs.filter(c => !dismissed.has(c.user_id))
  const totalUnread = visible.reduce((sum, c) => sum + c.unread, 0)

  return (
    <div style={{ maxWidth: 780, margin: "0 auto", padding: "20px 16px" }}>
      {/* Page header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 24 }}>💬</span>
          <div>
            <h2 style={{ margin: 0, fontSize: 18, color: "var(--text-main)" }}>
              กล่องข้อความ
            </h2>
            <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
              {loading ? "กำลังโหลด..." : `${visible.length} การสนทนา`}
              {totalUnread > 0 && (
                <span style={{
                  marginLeft: 8,
                  background: "#f44336", color: "#fff",
                  fontSize: 10, fontWeight: 700,
                  borderRadius: 10, padding: "1px 6px",
                }}>
                  {totalUnread} ยังไม่ตอบ
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          onClick={loadConvs}
          style={{
            padding: "6px 14px",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border)",
            borderRadius: 6, cursor: "pointer",
            color: "var(--text-muted)", fontSize: 12,
          }}
        >
          🔄 รีเฟรช
        </button>
      </div>

      {/* Blink keyframe (injected once) */}
      <style>{`
        @keyframes chatBlink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.1; }
        }
      `}</style>

      {loading ? (
        <div style={{ textAlign: "center", paddingTop: 60, color: "var(--text-muted)" }}>
          <div className="loading-spinner" style={{ margin: "0 auto 10px" }} />
          กำลังโหลด...
        </div>
      ) : visible.length === 0 ? (
        <div style={{
          textAlign: "center", paddingTop: 60,
          color: "var(--text-muted)", fontSize: 14,
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>📭</div>
          <div>ไม่มีการสนทนา</div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {visible.map(conv => (
            <ConvCard
              key={conv.user_id}
              conv={conv}
              onDismiss={handleDismiss}
            />
          ))}
        </div>
      )}
    </div>
  )
}
