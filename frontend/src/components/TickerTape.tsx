/**
 * components/TickerTape.tsx
 * แถบวิ่งแสดงดัชนีตลาดด้านล่างหน้าจอ — เหมือนหน้าจอในตลาดหุ้น
 * อัปเดตทุก 5 นาที | animation CSS ไม่ใช้ JS loop
 */
import { useState, useEffect } from "react"
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
  const [items, setItems]     = useState<TickerItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch(`${API_BASE}/ticker/`)
        const d   = await res.json()
        if (!cancelled && d.items?.length) {
          setItems(d.items)
        }
      } catch (e) { console.warn("Ticker fetch error:", e) }
      if (!cancelled) setLoading(false)
    }

    load()
    const interval = setInterval(load, 5 * 60 * 1000) // 5 นาที
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  if (loading || items.length === 0) return null

  // ทำซ้ำ items 3 รอบ — animation เลื่อน 1/3 แรกแล้ว reset
  const display = [...items, ...items, ...items]
  // คำนวณความกว้างต่อ item ≈ 180px × จำนวน items
  const itemW   = 180
  const totalW  = items.length * itemW          // กว้าง 1 รอบ (px)
  const dur     = Math.max(30, items.length * 4) // วินาที

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
        zIndex: 1,
      }}>
        <span style={{ animation: "pulse 1.5s ease-in-out infinite", fontSize: 7 }}>●</span> LIVE
      </div>

      {/* Scroll track — กว้างเท่า 3 รอบ เลื่อน 1 รอบแล้ว reset */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        <div style={{
          display: "flex", alignItems: "center",
          width: `${totalW * 3}px`,
          animation: `tickerScroll ${dur}s linear infinite`,
        }}>
          {display.map((item, i) => (
            <div key={`${item.symbol}-${i}`} style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "0 16px", height: 30, flexShrink: 0,
              borderRight: "1px solid #0d2137",
              fontSize: 11,
            }}>
              <span style={{ color: "#6a9bb5", fontSize: 10 }}>
                {item.label}
              </span>
              <span style={{
                fontFamily: "monospace", fontWeight: 700, fontSize: 12,
                color: item.up ? "#00e676" : "#ff5252",
              }}>
                {fmtPrice(item.price, item.type)}
              </span>
              <span style={{
                fontSize: 10, fontFamily: "monospace",
                color: item.up ? "#00c853" : "#ff1744",
              }}>
                {item.up ? "▲" : "▼"}{Math.abs(item.change_pct).toFixed(2)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes tickerScroll {
          0%   { transform: translateX(0); }
          100% { transform: translateX(-${totalW}px); }
        }
        @keyframes pulse {
          0%,100% { opacity:1; } 50% { opacity:.3; }
        }
      `}</style>
    </div>
  )
}
