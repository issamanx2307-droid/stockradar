import { cloneElement, createContext, isValidElement, useContext, useEffect, useMemo, useRef, useState } from "react"
import { api } from "../api/client"
import { StockTermInfo } from "../api/types"

type TermContextValue = {
  enabled: boolean
  setEnabled: (v: boolean) => void
  getDefinition: (termKey: string) => Promise<StockTermInfo | null>
  resolveTermKey: (token: string) => string | null
  matchRegex: RegExp | null
}

const LS_KEY = "term_assistant_enabled"

function loadEnabled() {
  const v = localStorage.getItem(LS_KEY)
  return v === null ? true : v === "1"
}

function saveEnabled(v: boolean) {
  localStorage.setItem(LS_KEY, v ? "1" : "0")
}

const TermContext = createContext<TermContextValue | null>(null)

function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function normalizeToken(s: string) {
  return (s || "").trim().toUpperCase()
}

function mapTokenToKey(token: string) {
  const t = normalizeToken(token)
  if (!t) return null
  if (t.startsWith("EMA")) return "EMA"
  if (t.startsWith("RSI")) return "RSI"
  if (t.startsWith("MACD")) return "MACD"
  if (t === "BB" || t.startsWith("BB_") || t.startsWith("BB")) return "BB"
  if (t.startsWith("ATR")) return "ATR"
  if (t.startsWith("ADX")) return "ADX"
  if (t === "HH20" || t === "LL20" || t === "HH20/LL20") return "HH20/LL20"
  if (t.includes("LONGTERM") || t.includes("SHORTTERM")) return "LONGTERM-SHORTTERM"
  return t
}

export function TermAssistantProvider({ children }: { children: React.ReactNode }) {
  const [enabled, setEnabledState] = useState(loadEnabled())
  const [terms, setTerms] = useState<StockTermInfo[]>([])
  const cacheRef = useRef<Map<string, StockTermInfo>>(new Map())
  const tokenToKeyRef = useRef<Map<string, string>>(new Map())

  useEffect(() => {
    saveEnabled(enabled)
  }, [enabled])

  useEffect(() => {
    api.getFeaturedTerms()
      .then(r => {
        const list = r.results || []
        setTerms(list)
        const m = new Map<string, StockTermInfo>()
        const tk = new Map<string, string>()
        for (const item of list) {
          const key = normalizeToken(item.term)
          if (key) m.set(key, item)
          tk.set(key, key)
          for (const kw of item.keywords || []) {
            const k = normalizeToken(kw)
            if (k) tk.set(k, key)
          }
        }
        cacheRef.current = m
        tokenToKeyRef.current = tk
      })
      .catch(() => {
        setTerms([])
      })
  }, [])

  const matchRegex = useMemo(() => {
    const tokens: string[] = []
    for (const t of terms) {
      if (t.term) tokens.push(t.term)
      for (const kw of t.keywords || []) tokens.push(kw)
    }
    const uniq = Array.from(new Set(tokens.map(normalizeToken))).filter(Boolean)
    if (uniq.length === 0) return null
    uniq.sort((a, b) => b.length - a.length)
    const pattern = uniq.map(escapeRegExp).join("|")
    return new RegExp(`(?<![A-Za-z0-9_])(${pattern})(?![A-Za-z0-9_])`, "gi")
  }, [terms])

  async function getDefinition(termKey: string) {
    const key = normalizeToken(termKey)
    if (!key) return null
    const cached = cacheRef.current.get(key)
    if (cached) return cached
    try {
      const data = await api.getTerm(key)
      cacheRef.current.set(key, data)
      tokenToKeyRef.current.set(key, key)
      return data
    } catch {
      return null
    }
  }

  function resolveTermKey(token: string) {
    const t = normalizeToken(token)
    if (!t) return null
    const mapped = tokenToKeyRef.current.get(t)
    if (mapped) return mapped
    return mapTokenToKey(t)
  }

  const value: TermContextValue = {
    enabled,
    setEnabled: setEnabledState,
    getDefinition,
    resolveTermKey,
    matchRegex,
  }

  return <TermContext.Provider value={value}>{children}</TermContext.Provider>
}

export function useTermAssistant() {
  const ctx = useContext(TermContext)
  if (!ctx) throw new Error("TermAssistantProvider is missing")
  return ctx
}

export function TermText({ text }: { text: string }) {
  const { enabled, matchRegex } = useTermAssistant()
  if (!enabled || !matchRegex) return <>{text}</>

  const parts: React.ReactNode[] = []
  let lastIndex = 0
  const s = text || ""
  const re = new RegExp(matchRegex.source, matchRegex.flags)
  let m: RegExpExecArray | null
  while ((m = re.exec(s)) !== null) {
    const start = m.index
    const end = start + m[0].length
    if (start > lastIndex) parts.push(s.slice(lastIndex, start))
    const token = m[0]
    parts.push(<AiTerm key={`${start}-${end}`} token={token}>{token}</AiTerm>)
    lastIndex = end
    if (re.lastIndex === start) re.lastIndex++
  }
  if (lastIndex < s.length) parts.push(s.slice(lastIndex))
  return <>{parts}</>
}

const SKIP_TAGS = new Set([
  "input",
  "textarea",
  "select",
  "option",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
  "svg",
  "path",
  "g",
  "text",
  "tspan",
  "canvas",
  "pre",
  "code",
])

function highlightNode(node: React.ReactNode): React.ReactNode {
  if (node === null || node === undefined || typeof node === "boolean") return node
  if (typeof node === "string") return <TermText text={node} />
  if (typeof node === "number") return node
  if (Array.isArray(node)) return node.map((c) => highlightNode(c))
  if (!isValidElement<any>(node)) return node

  const element = node as any

  if (element.type === TermText || element.type === AiTerm) return element
  if (typeof element.type === "string" && SKIP_TAGS.has(element.type)) return element
  if (element.props?.dangerouslySetInnerHTML) return element

  if (element.props?.children === undefined) return element
  const nextChildren = highlightNode(element.props.children)
  if (nextChildren === element.props.children) return element

  return cloneElement(element, element.props, nextChildren)
}

export function AutoTermHighlight({ children }: { children: React.ReactNode }) {
  const { enabled } = useTermAssistant()
  if (!enabled) return <>{children}</>
  return <>{highlightNode(children)}</>
}

export function AiTerm({ token, children }: { token: string; children: React.ReactNode }) {
  const { enabled, resolveTermKey, getDefinition } = useTermAssistant()
  const [open, setOpen] = useState(false)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [data, setData] = useState<StockTermInfo | null>(null)
  const timerRef = useRef<number | null>(null)

  function clearTimer() {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  function onEnter(e: React.MouseEvent) {
    if (!enabled) return
    const key = resolveTermKey(token)
    if (!key) return
    setPos({ x: e.clientX, y: e.clientY })
    clearTimer()
    timerRef.current = window.setTimeout(async () => {
      const d = await getDefinition(key)
      if (!d) return
      setData(d)
      setOpen(true)
    }, 300)
  }

  function onMove(e: React.MouseEvent) {
    if (!enabled) return
    if (!open) return
    setPos({ x: e.clientX, y: e.clientY })
  }

  function onLeave() {
    clearTimer()
    setOpen(false)
  }

  return (
    <span className="ai-term" onMouseEnter={onEnter} onMouseMove={onMove} onMouseLeave={onLeave}>
      {children}
      {open && data && (
        <span className="ai-tooltip" style={{ left: pos.x + 12, top: pos.y + 12 }}>
          <div className="ai-tooltip-title">{data.term}</div>
          <div className="ai-tooltip-body">{data.short_definition}</div>
        </span>
      )}
    </span>
  )
}

export function TermAssistantToggle() {
  const { enabled, setEnabled } = useTermAssistant()
  return (
    <button className="btn btn-ghost" onClick={() => setEnabled(!enabled)}>
      {enabled ? "💡 คำใบ้: เปิด" : "💡 คำใบ้: ปิด"}
    </button>
  )
}
