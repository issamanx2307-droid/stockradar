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

// Fallback แสดงเสมอเมื่อ API ยังไม่มีข้อมูล
const FALLBACK_ITEMS: TickerItem[] = [
  { symbol:"^GSPC",    label:"S&P 500",   type:"index",     price:5300,   change:12,    change_pct:0.23,  up:true  },
  { symbol:"^DJI",     label:"Dow Jones", type:"index",     price:39500,  change:-45,   change_pct:-0.11, up:false },
  { symbol:"^IXIC",    label:"NASDAQ",    type:"index",     price:16800,  change:55,    change_pct:0.33,  up:true  },
  { symbol:"^SET.BK",  label:"SET",       type:"index",     price:1380,   change:-3,    change_pct:-0.22, up:false },
  { symbol:"^N225",    label:"Nikkei",    type:"index",     price:38200,  change:180,   change_pct:0.47,  up:true  },
  { symbol:"^HSI",     label:"Hang Seng", type:"index",     price:17100,  change:-90,   change_pct:-0.52, up:false },
  { symbol:"GC=F",     label:"Gold",      type:"commodity", price:2320,   change:8.5,   change_pct:0.37,  up:true  },
  { symbol:"CL=F",     label:"Oil (WTI)", type:"commodity", price:78.5,   change:-0.4,  change_pct:-0.51, up:false },
  { symbol:"THBUSD=X", label:"USD/THB",   type:"fx",        price:34.82,  change:0.05,  change_pct:0.14,  up:true  },
  { symbol:"EURUSD=X", label:"EUR/USD",   type:"fx",        price:1.0865, change:-0.002,change_pct:-0.18, up:false },
  { symbol:"BTC-USD",  label:"Bitcoin",   type:"crypto",    price:67200,  change:850,   change_pct:1.28,  up:true  },
  { symbol:"ETH-USD",  label:"Ethereum",  type:"crypto",    price:3520,   change:-25,   change_pct:-0.71, up:false },
]

export default function TickerTape() {
  const [items, setItems]       = useState<TickerItem[]>(FALLBACK_ITEMS)
  const [isLive, setIsLive]     = useState(false)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const res = await fetch(`${API_BASE}/ticker/`)
        const d   = await res.json()
        if (!cancelled && d.items?.length) {
          setItems(d.items)
          setIsLive(true)
        }
      } catch (e) { console.warn("Ticker fetch error:", e) }
    }

    load()
    const interval = setInterval(load, 5 * 60 * 1000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  if (items.length === 0) return null

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
        fontSize: 10, fontWeight: 700, letterSpacing: 1,
        color: isLive ? "#00d4ff" : "#ffd740",
        zIndex: 1,
      }}>
        <span style={{ animation: "pulse 1.5s ease-in-out infinite", fontSize: 7 }}>●</span>
        {isLive ? "LIVE" : "MARKET"}
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
