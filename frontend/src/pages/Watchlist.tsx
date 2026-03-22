/**
 * pages/Watchlist.tsx — พอร์ตส่วนตัว สูงสุด 10 หุ้น
 * ใส่ราคาซื้อ+จำนวนได้ไม่จำกัดครั้ง → คำนวณต้นทุนเฉลี่ย + วิเคราะห์ + แนะนำ
 */
import { useState, useEffect, useCallback, useRef } from "react"

const BASE = "http://127.0.0.1:8000/api"

type Trade = { id: number; action: string; price: number; quantity: number; trade_date: string; note: string }
type Item  = {
  item_id: number; symbol: string; symbol_name: string; exchange: string
  current_price: number | null; price_date: string
  avg_cost: number; total_qty: number; total_invested: number; realized_pnl: number
  unrealized_pnl: number; unrealized_pnl_pct: number; market_value: number
  stop_loss: number; atr: number
  action: string; action_label: string; reasons: string[]
  buy_more_price: number | null; buy_more_reason: string
  rsi: number; adx: number; ema20: number|null; ema50: number|null; ema200: number|null
  alert_high: number|null; alert_low: number|null; note: string
  trades: Trade[]
  error?: string
}
type Summary = { total_invested: number; total_market: number; total_pnl: number; total_pnl_pct: number }

const ACTION_COLOR: Record<string, string> = {
  BUY_MORE:    "#00c853", HOLD_STRONG: "#00e676",
  HOLD:        "#ffd600", REVIEW:      "#ff9100",
  TAKE_PROFIT: "#00b0ff", SELL:        "#ff5252",
}

function pct(v: number) {
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`
}
function thb(v: number) {
  return `฿${v.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function Watchlist({ onOpenChart }: { onOpenChart?: (s: string) => void }) {
  const [items, setItems]         = useState<Item[]>([])
  const [summary, setSummary]     = useState<Summary | null>(null)
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState("")
  const [livePrices, setLive]     = useState<Record<string, number>>({})
  const [liveTime, setLiveTime]   = useState<string>("")
  const wsRef                     = useRef<WebSocket | null>(null)

  // ── Add stock ──
  const [addSymbol, setAddSymbol] = useState("")
  const [addErr, setAddErr]       = useState("")
  const [addLoading, setAddLoading] = useState(false)

  const [expanded, setExpanded]   = useState<number | null>(null)
  const [tradeForm, setTradeForm] = useState<Record<number, { action:string; price:string; qty:string; date:string; note:string }>>({})
  const [calcForm, setCalcForm]   = useState<Record<number, { price:string; qty:string }>>({})
  const [calcResult, setCalcResult] = useState<Record<number, any>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${BASE}/watchlist/`)
      const d   = await res.json()
      setItems(d.items || [])
      setSummary(d.summary || null)

      // request live prices via WebSocket
      const syms = (d.items || []).map((i: Item) => i.symbol)
      if (syms.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "poll_prices", symbols: syms }))
      }
    } catch (e: any) { setError(e.message) }
    setLoading(false)
  }, [])

  // ── WebSocket for live prices ──
  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8000/ws/radar/")
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === "prices" && Array.isArray(msg.data)) {
          const map: Record<string, number> = {}
          msg.data.forEach((p: any) => { if (p.symbol && p.price) map[p.symbol] = p.price })
          setLive(prev => ({ ...prev, ...map }))
          setLiveTime(new Date().toLocaleTimeString("th-TH"))
        }
      } catch (_) {}
    }
    ws.onopen = () => load()
    ws.onerror = () => load()  // fallback ถ้า WS ไม่พร้อม
    return () => ws.close()
  }, [load])

  async function handleAdd() {
    if (!addSymbol.trim()) return
    setAddLoading(true); setAddErr("")
    try {
      const res  = await fetch(`${BASE}/watchlist/add/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: addSymbol.trim().toUpperCase() })
      })
      const d = await res.json()
      if (!res.ok) { setAddErr(d.error || "เกิดข้อผิดพลาด"); setAddLoading(false); return }
      setAddSymbol(""); await load()
    } catch (e: any) { setAddErr(e.message) }
    setAddLoading(false)
  }

  async function handleRemove(itemId: number, sym: string) {
    if (!confirm(`ลบ ${sym} ออกจาก Watchlist?`)) return
    await fetch(`${BASE}/watchlist/item/${itemId}/`, { method: "DELETE" })
    await load()
  }

  async function handleAddTrade(itemId: number) {
    const f = tradeForm[itemId] || {}
    if (!f.price || !f.qty) return alert("กรุณากรอกราคาและจำนวน")
    const res = await fetch(`${BASE}/watchlist/item/${itemId}/trade/`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: f.action || "BUY", price: parseFloat(f.price),
        quantity: parseInt(f.qty), trade_date: f.date || new Date().toISOString().slice(0,10),
        note: f.note || ""
      })
    })
    if (res.ok) { setTradeForm(p => ({ ...p, [itemId]: { action:"BUY",price:"",qty:"",date:"",note:"" } })); await load() }
    else { const d = await res.json(); alert(d.error || "บันทึกล้มเหลว") }
  }

  async function handleDeleteTrade(tradeId: number) {
    if (!confirm("ลบรายการซื้อนี้?")) return
    await fetch(`${BASE}/watchlist/item/0/trade/`, { method: "DELETE" })  // placeholder
    await load()
  }

  async function handleCalcSell(itemId: number) {
    const f = calcForm[itemId] || {}
    if (!f.price) return
    const res = await fetch(`${BASE}/watchlist/item/${itemId}/calc-sell/`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sell_price: parseFloat(f.price), sell_qty: f.qty ? parseInt(f.qty) : undefined })
    })
    const d = await res.json()
    setCalcResult(p => ({ ...p, [itemId]: d }))
  }

  async function handleUpdateAlert(itemId: number, high: string, low: string) {
    await fetch(`${BASE}/watchlist/item/${itemId}/alert/`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alert_price_high: high || null, alert_price_low: low || null })
    })
    await load()
  }

  const pnlColor = (v: number) => v >= 0 ? "var(--green)" : "var(--red)"
  const tf = (id: number) => tradeForm[id] || { action:"BUY", price:"", qty:"", date:"", note:"" }
  const cf = (id: number) => calcForm[id]  || { price:"", qty:"" }

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">⭐ Watchlist — พอร์ตส่วนตัว</div>
        <div className="page-subtitle">ติดตามหุ้นสูงสุด 10 ตัว · บันทึกการซื้อได้ไม่จำกัด · คำนวณต้นทุนเฉลี่ยอัตโนมัติ</div>
      </div>
      <div className="page-body">

        {/* ── Summary ── */}
        {summary && (
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
            {[
              { label:"ต้นทุนรวม",   val: thb(summary.total_invested), color:"var(--accent)" },
              { label:"มูลค่าตลาด",  val: thb(summary.total_market),   color:"var(--text-primary)" },
              { label:"กำไร/ขาดทุน", val: thb(summary.total_pnl),      color: pnlColor(summary.total_pnl) },
              { label:"ผลตอบแทน",   val: pct(summary.total_pnl_pct),  color: pnlColor(summary.total_pnl_pct) },
            ].map(({ label, val, color }) => (
              <div key={label} className="card" style={{ textAlign:"center", padding:"12px 8px" }}>
                <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>{label}</div>
                <div style={{ fontSize:20, fontWeight:700, fontFamily:"var(--font-mono)", color }}>{val}</div>
              </div>
            ))}
          </div>
        )}
        {liveTime && (
          <div style={{ fontSize:11, color:"var(--green)", marginBottom:12, display:"flex", alignItems:"center", gap:6 }}>
            <span style={{ width:6, height:6, borderRadius:"50%", background:"var(--green)", display:"inline-block" }} />
            Live price อัปเดตล่าสุด {liveTime} · delay ~15 นาที
          </div>
        )}

        {/* ── Add Stock ── */}
        <div className="card" style={{ marginBottom:16 }}>
          <div className="card-title">➕ เพิ่มหุ้ว ({items.length}/10)</div>
          <div style={{ display:"flex", gap:10, alignItems:"center" }}>
            <input className="filter-input" placeholder="รหัสหุ้น เช่น PTT, AAPL..."
              value={addSymbol} onChange={e => setAddSymbol(e.target.value.toUpperCase())}
              onKeyDown={e => e.key==="Enter" && handleAdd()}
              style={{ flex:1, fontFamily:"var(--font-mono)", fontWeight:700, fontSize:14 }} />
            <button className="btn btn-primary" onClick={handleAdd}
              disabled={addLoading || items.length >= 10} style={{ minWidth:100 }}>
              {addLoading ? "⏳..." : "เพิ่ม"}
            </button>
          </div>
          {addErr && <div style={{ color:"var(--red)", fontSize:12, marginTop:6 }}>❌ {addErr}</div>}
        </div>

        {/* ── Item List ── */}
        {loading ? (
          <div className="loading-state"><div className="loading-spinner" /><span>กำลังโหลด...</span></div>
        ) : items.length === 0 ? (
          <div className="empty-state">
            <span style={{ fontSize:48 }}>⭐</span>
            <span>ยังไม่มีหุ้วใน Watchlist</span>
            <span style={{ fontSize:12, color:"var(--text-muted)" }}>เพิ่มรหัสหุ้วด้านบนเพื่อเริ่มติดตาม</span>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
            {items.map(item => {
              const isOpen    = expanded === item.item_id
              const livePrice = livePrices[item.symbol] || item.current_price
              const actColor  = ACTION_COLOR[item.action] || "var(--text-muted)"
              const pnlPct    = livePrice && item.avg_cost > 0
                ? (livePrice - item.avg_cost) / item.avg_cost * 100
                : item.unrealized_pnl_pct
              const unrealPnl = livePrice && item.avg_cost > 0
                ? (livePrice - item.avg_cost) * item.total_qty
                : item.unrealized_pnl
              const alertH    = item.alert_high
              const alertL    = item.alert_low
              const priceHit  = livePrice && alertH && livePrice >= alertH
              const priceLow  = livePrice && alertL && livePrice <= alertL
              const isLive    = !!livePrices[item.symbol]

              return (
                <div key={item.item_id} className="card" style={{
                  borderLeft: `3px solid ${actColor}`,
                  background: priceHit ? "rgba(0,200,83,0.05)" : priceLow ? "rgba(255,82,82,0.05)" : undefined
                }}>
                  {/* ── Header Row ── */}
                  <div style={{ display:"flex", alignItems:"center", gap:12, marginBottom: isOpen ? 16 : 0 }}>
                    <div style={{ flex:1, cursor:"pointer" }} onClick={() => setExpanded(isOpen ? null : item.item_id)}>
                      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                        <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, fontSize:18, color:"var(--accent)" }}>
                          {item.symbol}
                        </span>
                        <span style={{ fontSize:11, color:"var(--text-muted)" }}>{item.symbol_name}</span>
                        <span style={{ fontSize:10, padding:"1px 6px", borderRadius:4,
                          background:"var(--bg-elevated)", color:"var(--text-muted)" }}>{item.exchange}</span>
                        {priceHit && <span style={{ fontSize:10, padding:"2px 6px", borderRadius:4,
                          background:"rgba(0,200,83,0.15)", color:"#00c853" }}>🔔 ถึงราคาสูง</span>}
                        {priceLow && <span style={{ fontSize:10, padding:"2px 6px", borderRadius:4,
                          background:"rgba(255,82,82,0.15)", color:"var(--red)" }}>🔔 ต่ำกว่าเป้า</span>}
                      </div>
                      <div style={{ display:"flex", gap:20, marginTop:6, fontSize:12 }}>
                        <span>ราคา: <b style={{ fontFamily:"var(--font-mono)" }}>
                          {item.current_price ? thb(item.current_price) : "—"}
                        </b></span>
                        {item.avg_cost > 0 && <>
                          <span>ต้นทุน: <b style={{ fontFamily:"var(--font-mono)" }}>{thb(item.avg_cost)}</b></span>
                          <span>จำนวน: <b style={{ fontFamily:"var(--font-mono)" }}>{item.total_qty.toLocaleString()}</b></span>
                          <span style={{ color: pnlColor(pnlPct), fontWeight:700 }}>
                            {pct(pnlPct)} ({thb(item.unrealized_pnl)})
                          </span>
                        </>}
                      </div>
                    </div>
                    {/* Action badge */}
                    <div style={{ textAlign:"right", flexShrink:0 }}>
                      <div style={{ fontSize:13, fontWeight:700, color:actColor, marginBottom:4 }}>
                        {item.action_label}
                      </div>
                      <div style={{ display:"flex", gap:6 }}>
                        {onOpenChart && (
                          <button className="btn btn-ghost" style={{ fontSize:11, padding:"3px 8px" }}
                            onClick={() => onOpenChart(item.symbol)}>📈 กราฟ</button>
                        )}
                        <button className="btn btn-ghost" style={{ fontSize:11, padding:"3px 8px", color:"var(--red)" }}
                          onClick={() => handleRemove(item.item_id, item.symbol)}>ลบ</button>
                      </div>
                    </div>
                  </div>

                  {/* ── Expanded Detail ── */}
                  {isOpen && (
                    <div style={{ borderTop:"1px solid var(--border)", paddingTop:16 }}>
                      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:16, marginBottom:16 }}>

                        {/* Analysis */}
                        <div>
                          <div style={{ fontSize:12, fontWeight:700, color:"var(--text-muted)", marginBottom:8 }}>📊 วิเคราะห์</div>
                          {[
                            { label:"ต้นทุนเฉลี่ย", val: item.avg_cost > 0 ? thb(item.avg_cost) : "—", color:"var(--text-primary)" },
                            { label:"Stop Loss",    val: item.stop_loss > 0 ? thb(item.stop_loss) : "—", color:"var(--red)" },
                            { label:"RSI",          val: item.rsi ? `${item.rsi.toFixed(1)}` : "—", color: item.rsi < 30 ? "var(--blue)" : item.rsi > 70 ? "var(--red)" : "var(--text-primary)" },
                            { label:"ADX",          val: item.adx ? `${item.adx.toFixed(1)}` : "—", color:"var(--text-primary)" },
                            { label:"EMA20/50/200", val: `${item.ema20?.toFixed(1)||"—"}/${item.ema50?.toFixed(1)||"—"}/${item.ema200?.toFixed(1)||"—"}`, color:"var(--text-secondary)" },
                          ].map(({ label, val, color }) => (
                            <div key={label} style={{ display:"flex", justifyContent:"space-between",
                              fontSize:12, borderBottom:"1px solid var(--border)", padding:"4px 0" }}>
                              <span style={{ color:"var(--text-muted)" }}>{label}</span>
                              <span style={{ fontFamily:"var(--font-mono)", fontWeight:600, color }}>{val}</span>
                            </div>
                          ))}
                          {item.reasons.map((r,i) => (
                            <div key={i} style={{ fontSize:11, color:actColor, marginTop:6 }}>• {r}</div>
                          ))}
                          {item.buy_more_price && (
                            <div style={{ fontSize:11, color:"var(--green)", marginTop:4 }}>
                              🟢 ซื้อเพิ่มที่ {thb(item.buy_more_price)} — {item.buy_more_reason}
                            </div>
                          )}
                        </div>

                        {/* Add Trade */}
                        <div>
                          <div style={{ fontSize:12, fontWeight:700, color:"var(--text-muted)", marginBottom:8 }}>📝 บันทึกการซื้อ/ขาย</div>
                          <div style={{ display:"flex", gap:6, marginBottom:6 }}>
                            {["BUY","SELL"].map(a => (
                              <button key={a} onClick={() => setTradeForm(p => ({ ...p, [item.item_id]: { ...tf(item.item_id), action:a } }))}
                                style={{ flex:1, padding:"4px 0", fontSize:11, fontWeight:700, borderRadius:6, cursor:"pointer",
                                  border:`1px solid ${tf(item.item_id).action===a ? (a==="BUY"?"var(--green)":"var(--red)") : "var(--border)"}`,
                                  background: tf(item.item_id).action===a ? (a==="BUY"?"rgba(0,230,118,0.12)":"rgba(255,82,82,0.12)") : "transparent",
                                  color: tf(item.item_id).action===a ? (a==="BUY"?"var(--green)":"var(--red)") : "var(--text-muted)" }}>
                                {a==="BUY"?"🟢 ซื้อ":"🔴 ขาย"}
                              </button>
                            ))}
                          </div>
                          {[
                            { key:"price", placeholder:"ราคา", type:"number" },
                            { key:"qty",   placeholder:"จำนวนหุ้น", type:"number" },
                            { key:"date",  placeholder:"วันที่ (YYYY-MM-DD)", type:"date" },
                            { key:"note",  placeholder:"หมายเหตุ (optional)", type:"text" },
                          ].map(({ key, placeholder, type }) => (
                            <input key={key} type={type} placeholder={placeholder}
                              className="filter-input" style={{ width:"100%", marginBottom:4, fontSize:12 }}
                              value={(tf(item.item_id) as any)[key]}
                              onChange={e => setTradeForm(p => ({ ...p, [item.item_id]: { ...tf(item.item_id), [key]: e.target.value } }))} />
                          ))}
                          <button className="btn btn-primary" style={{ width:"100%", fontSize:12 }}
                            onClick={() => handleAddTrade(item.item_id)}>บันทึก</button>

                          {/* Trade history */}
                          {item.trades.length > 0 && (
                            <div style={{ marginTop:10 }}>
                              <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>ประวัติ</div>
                              {item.trades.map(t => (
                                <div key={t.id} style={{ display:"flex", gap:8, fontSize:11,
                                  padding:"3px 0", borderBottom:"1px solid var(--border)" }}>
                                  <span style={{ color: t.action==="BUY"?"var(--green)":"var(--red)", fontWeight:700 }}>{t.action}</span>
                                  <span style={{ fontFamily:"var(--font-mono)" }}>{thb(t.price)}</span>
                                  <span>×{t.quantity.toLocaleString()}</span>
                                  <span style={{ color:"var(--text-muted)", flex:1 }}>{t.trade_date}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Calc Sell */}
                        <div>
                          <div style={{ fontSize:12, fontWeight:700, color:"var(--text-muted)", marginBottom:8 }}>💰 คำนวณ ถ้าขายที่ราคา x จำนวน y</div>
                          <input type="number" placeholder="ราคาขาย" className="filter-input"
                            style={{ width:"100%", marginBottom:4, fontSize:12 }}
                            value={cf(item.item_id).price}
                            onChange={e => setCalcForm(p => ({ ...p, [item.item_id]: { ...cf(item.item_id), price:e.target.value } }))} />
                          <input type="number" placeholder={`จำนวน (ทั้งหมด ${item.total_qty})`}
                            className="filter-input" style={{ width:"100%", marginBottom:6, fontSize:12 }}
                            value={cf(item.item_id).qty}
                            onChange={e => setCalcForm(p => ({ ...p, [item.item_id]: { ...cf(item.item_id), qty:e.target.value } }))} />
                          <button className="btn btn-ghost" style={{ width:"100%", fontSize:12 }}
                            onClick={() => handleCalcSell(item.item_id)}>คำนวณ</button>

                          {calcResult[item.item_id] && (() => {
                            const r = calcResult[item.item_id]
                            return (
                              <div style={{ marginTop:10, padding:"10px 12px",
                                background: r.is_profit ? "rgba(0,200,83,0.1)" : "rgba(255,82,82,0.1)",
                                borderRadius:8, border:`1px solid ${r.is_profit?"var(--green)":"var(--red)"}` }}>
                                {[
                                  { label:"รายรับ (หลังค่าคอม)", val: thb(r.net_revenue) },
                                  { label:"ต้นทุน",             val: thb(r.cost_basis)  },
                                  { label:"กำไร/ขาดทุน",        val: thb(r.pnl), bold:true, color: r.is_profit?"var(--green)":"var(--red)" },
                                  { label:"ผลตอบแทน",          val: pct(r.pnl_pct), color: r.is_profit?"var(--green)":"var(--red)" },
                                  { label:"ค่าคอมมิชชั่น",     val: thb(r.commission) },
                                  { label:"เหลือในพอร์ต",      val: `${r.remaining_qty} หุ้น` },
                                ].map(({ label, val, bold, color }) => (
                                  <div key={label} style={{ display:"flex", justifyContent:"space-between", fontSize:12, padding:"2px 0" }}>
                                    <span style={{ color:"var(--text-muted)" }}>{label}</span>
                                    <span style={{ fontFamily:"var(--font-mono)", fontWeight: bold ? 700 : 600, color: color || "var(--text-primary)" }}>{val}</span>
                                  </div>
                                ))}
                              </div>
                            )
                          })()}

                          {/* Alert settings */}
                          <div style={{ marginTop:12 }}>
                            <div style={{ fontSize:11, color:"var(--text-muted)", marginBottom:4 }}>🔔 Alert ราคา</div>
                            <div style={{ display:"flex", gap:6, marginBottom:4 }}>
                              <input type="number" placeholder={`สูง (ปัจจุบัน ${alertH||"—"})`}
                                className="filter-input" style={{ flex:1, fontSize:11 }}
                                id={`ah-${item.item_id}`} defaultValue={alertH || ""} />
                              <input type="number" placeholder={`ต่ำ (ปัจจุบัน ${alertL||"—"})`}
                                className="filter-input" style={{ flex:1, fontSize:11 }}
                                id={`al-${item.item_id}`} defaultValue={alertL || ""} />
                            </div>
                            <button className="btn btn-ghost" style={{ width:"100%", fontSize:11 }}
                              onClick={() => {
                                const h = (document.getElementById(`ah-${item.item_id}`) as HTMLInputElement)?.value
                                const l = (document.getElementById(`al-${item.item_id}`) as HTMLInputElement)?.value
                                handleUpdateAlert(item.item_id, h, l)
                              }}>บันทึก Alert</button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
