/**
 * components/SymbolInput.tsx
 * Reusable symbol autocomplete input — ใช้ได้ทุกหน้า
 * ดึงข้อมูลจาก /api/symbols/ แสดง dropdown พร้อม flag, ชื่อ, ตลาด
 */
import { useState, useEffect, useRef, useCallback } from "react"
import { API_BASE } from "../api/config"

interface SymbolResult {
  symbol: string; name: string; exchange: string; sector?: string
}

interface Props {
  value: string
  onChange: (v: string) => void
  onSelect?: (sym: string) => void   // เรียกเมื่อเลือกจาก dropdown หรือกด Enter
  placeholder?: string
  style?: React.CSSProperties
  className?: string
  autoFocus?: boolean
  disabled?: boolean
}

const FLAG: Record<string, string> = { SET:"🇹🇭", NASDAQ:"🇺🇸", NYSE:"🇺🇸", mai:"🇹🇭" }
const EX_COLOR: Record<string, {bg:string;color:string}> = {
  SET:    { bg:"#0d4f3c", color:"#00e676" },
  mai:    { bg:"#0d3b2e", color:"#69f0ae" },
  NASDAQ: { bg:"#1a2c5e", color:"#7eb3ff" },
  NYSE:   { bg:"#122050", color:"#90caf9" },
}

export default function SymbolInput({
  value, onChange, onSelect,
  placeholder = "รหัสหุ้น เช่น PTT, KBANK, AAPL...",
  style, className = "filter-input", autoFocus, disabled,
}: Props) {
  const [results, setResults] = useState<SymbolResult[]>([])
  const [open, setOpen]       = useState(false)
  const [active, setActive]   = useState(-1)
  const timer  = useRef<any>(null)
  const wrap   = useRef<HTMLDivElement>(null)
  const input  = useRef<HTMLInputElement>(null)

  // ── Close on click outside ──
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (!wrap.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", h)
    return () => document.removeEventListener("mousedown", h)
  }, [])

  // ── Fetch suggestions ──
  const fetchSuggestions = useCallback((q: string) => {
    clearTimeout(timer.current)
    if (!q.trim()) { setResults([]); setOpen(false); return }
    timer.current = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API_BASE}/symbols/?search=${encodeURIComponent(q)}&page_size=10`
        )
        const d = await res.json()
        const items: SymbolResult[] = d.results || []
        setResults(items)
        setOpen(items.length > 0)
        setActive(-1)
      } catch { setResults([]) }
    }, 200)
  }, [])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value.toUpperCase()
    onChange(v)
    fetchSuggestions(v)
  }

  function pick(sym: string) {
    onChange(sym)
    setOpen(false)
    setResults([])
    onSelect?.(sym)
    input.current?.blur()
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open) {
      if (e.key === "Enter") onSelect?.(value)
      return
    }
    if (e.key === "ArrowDown") { e.preventDefault(); setActive(a => Math.min(a+1, results.length-1)) }
    if (e.key === "ArrowUp")   { e.preventDefault(); setActive(a => Math.max(a-1, -1)) }
    if (e.key === "Enter") {
      e.preventDefault()
      if (active >= 0 && results[active]) pick(results[active].symbol)
      else { setOpen(false); onSelect?.(value) }
    }
    if (e.key === "Escape") setOpen(false)
  }

  const exStyle = (ex: string) => EX_COLOR[ex] || { bg:"#1e2d42", color:"#aaa" }

  return (
    <div ref={wrap} style={{ position:"relative", ...style }}>
      <input
        ref={input}
        type="text"
        className={className}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => value && results.length > 0 && setOpen(true)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        disabled={disabled}
        autoComplete="off"
        spellCheck={false}
        style={{ width:"100%", fontFamily:"var(--font-mono)", fontWeight:700 }}
      />

      {/* Dropdown */}
      {open && results.length > 0 && (
        <div style={{
          position:"absolute", top:"calc(100% + 4px)", left:0, right:0, zIndex:1200,
          background:"var(--bg-surface,#1a2332)", border:"1px solid var(--border)",
          borderRadius:8, maxHeight:280, overflowY:"auto",
          boxShadow:"0 8px 32px rgba(0,0,0,.5)",
        }}>
          {results.map((s, i) => {
            const ex = exStyle(s.exchange)
            return (
              <div
                key={s.symbol}
                onMouseDown={() => pick(s.symbol)}
                onMouseEnter={() => setActive(i)}
                style={{
                  padding:"8px 12px", cursor:"pointer",
                  display:"flex", alignItems:"center", gap:10,
                  borderBottom:"1px solid var(--border)",
                  background: i === active ? "var(--bg-elevated)" : "transparent",
                  transition:"background .1s",
                }}
              >
                <span style={{ fontSize:15, flexShrink:0 }}>{FLAG[s.exchange] || "🌐"}</span>
                <span style={{
                  fontFamily:"var(--font-mono)", fontWeight:700, fontSize:14,
                  color:"var(--accent)", minWidth:64, flexShrink:0,
                }}>{s.symbol}</span>
                <span style={{
                  fontSize:12, color:"var(--text-muted)", flex:1,
                  overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap",
                }}>{s.name}</span>
                {s.sector && (
                  <span style={{ fontSize:10, color:"var(--text-muted)", flexShrink:0 }}>
                    {s.sector}
                  </span>
                )}
                <span style={{
                  fontSize:10, fontWeight:600, padding:"2px 7px", borderRadius:4,
                  flexShrink:0, background:ex.bg, color:ex.color,
                }}>{s.exchange}</span>
              </div>
            )
          })}
          <div style={{
            padding:"5px 12px", fontSize:10, color:"var(--text-muted)",
            borderTop:"1px solid var(--border)",
          }}>
            ↑↓ เลื่อน · Enter เลือก · Esc ปิด
          </div>
        </div>
      )}
    </div>
  )
}
