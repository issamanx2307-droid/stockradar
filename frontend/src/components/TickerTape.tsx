/**
 * components/TickerTape.tsx
 * แถบวิ่งแสดงดัชนีตลาดด้านล่างหน้าจอ — เหมือนหน้าจอในตลาดหุ้น
 * อัปเดตทุก 5 นาที | animation CSS ไม่ใช้ JS loop
 */
import { useState, useEffect, useRef } from "react"
import { API_BASE } from "../api/config"

interface TickerItem {
  symbol: string; label: string; type: string
  price: number; change: number; change_pct: number; up: boolean
}

// TYPE ICON
const TYPE_ICON: Record<string, string> = {
  index: "📊", commodity: "🛢️", fx: "💱", crypto: "₿"
}

function fmtPrice(price: number, type: string): string {
  if (type === "fx" || price < 10)    return price.toFixed(4)
  if (price < 1000)  return price.toFixed(2)
  return price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function TickerTape() {
  const [items, setItems]       = useState<TickerItem[]>([])
  const [loading, setLoading]   = useState(true)
  const [duration, setDuration] = useState(60) // วินาที
  const trackRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch(`${API_BASE}/ticker/`)
        const d   = await res.json()
        if (!cancelled && d.items?.length) {
          setItems(d.items)
          // คำนวณ duration ตามจำนวนรายการ (ยิ่งเยอะยิ่งช้า)
          setDuration(Math.max(40, d.items.length * 4))
        }
      } catch (e) { console.warn("Ticker fetch error:", e) }
      if (!cancelled) setLoading(false)
    }

    load()
    const interval = setInterval(load, 5 * 60 * 1000) // 5 นาที
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  if (loading || items.length === 0) return null

  // ทำซ้ำ items 3 รอบเพื่อให้ scroll ต่อเนื่อง
  const display = [...items, ...items, ...items]

  return (
    <div style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 1000,
      background: "#050d14",
      borderTop: "1px solid #0d2137",
      height: 30, overflow: "hidden",
      display: "flex", alignItems: "center",
    }}>
      {/* Label ซ้าย */}
      <div style={{
        flexShrink: 0, padding: "0 10px",
        background: "#0a1929", borderRight: "1px solid #0d2137",
        height: "100%", display: "flex", alignItems: "center", gap: 5,
        fontSize: 10, fontWeight: 700, color: "#00d4ff", letterSpacing: 1,
      }}>
        <span style={{ fontSize: 8 }}>●</span> LIVE
      </div>

      {/* Scroll track */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        <div
          ref={trackRef}
          style={{
            display: "flex", alignItems: "center", gap: 0, whiteSpace: "nowrap",
            animation: `tickerScroll ${duration}s linear infinite`,
          }}
        >
          {display.map((item, i) => (
            <span key={`${item.symbol}-${i}`} style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              padding: "0 18px", height: 30, borderRight: "1px solid #0d2137",
              fontSize: 11, cursor: "default",
            }}>
              {/* Label */}
              <span style={{ color: "#7ab3cc", fontSize: 10, letterSpacing: .5 }}>
                {TYPE_ICON[item.type]} {item.label}
              </span>
              {/* Price */}
              <span style={{
                fontFamily: "monospace", fontWeight: 700, fontSize: 12,
                color: item.up ? "#00e676" : "#ff5252",
              }}>
                {fmtPrice(item.price, item.type)}
              </span>
              {/* Change */}
              <span style={{
                fontSize: 10, fontFamily: "monospace",
                color: item.up ? "#00c853" : "#ff1744",
              }}>
                {item.up ? "▲" : "▼"} {Math.abs(item.change_pct).toFixed(2)}%
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* CSS animation */}
      <style>{`
        @keyframes tickerScroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-33.333%); }
        }
      `}</style>
    </div>
  )
}
