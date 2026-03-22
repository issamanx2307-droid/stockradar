import { useState, useEffect, useRef, useCallback } from "react"
import { createChart, CandlestickSeries, LineSeries, HistogramSeries, IChartApi, ISeriesApi } from "lightweight-charts"
import { api } from "../api/client"
import { PriceData, IndicatorData } from "../api/types"
import { AiTerm, TermText } from "../components/TermAssistant"

// ── Symbol Search ─────────────────────────────────────────────────────────────
function SymbolSearch({ onSelect }: { onSelect: (sym: string) => void }) {
  const [q, setQ] = useState("")
  const [results, setResults] = useState<any[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<any>(null)
  const wrapRef  = useRef<HTMLDivElement>(null)
  const FLAG: Record<string, string> = { SET:"🇹🇭", NASDAQ:"🇺🇸", NYSE:"🇺🇸", OTHER:"🌐" }

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", h)
    return () => document.removeEventListener("mousedown", h)
  }, [])

  useEffect(() => {
    clearTimeout(timerRef.current)
    if (!q.trim()) { setResults([]); setOpen(false); return }
    setLoading(true)
    timerRef.current = setTimeout(async () => {
      try {
        const res = await api.getSymbols({ search: q.trim(), page_size: "20" } as any)
        setResults((res as any).results || [])
        setOpen(true)
      } catch { setResults([]) }
      setLoading(false)
    }, 250)
  }, [q])

  function pick(sym: string) { setQ(sym); setOpen(false); onSelect(sym) }

  return (
    <div ref={wrapRef} style={{ position:"relative", width:280 }}>
      <input className="filter-input" placeholder="🔍 PTT, KBANK, AAPL..."
        value={q} onChange={e => setQ(e.target.value.toUpperCase())} autoComplete="off"
        onKeyDown={e => { if (e.key==="Enter" && q.trim()) pick(q.trim()); if (e.key==="Escape") setOpen(false) }}
        style={{ width:"100%", fontFamily:"var(--font-mono)", fontWeight:600 }} />
      {loading && <div style={{ position:"absolute", right:10, top:"50%", transform:"translateY(-50%)" }}>
        <div className="loading-spinner" style={{ width:14, height:14, borderWidth:2 }} /></div>}
      {open && results.length > 0 && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, zIndex:999,
          background:"var(--bg-surface,#1a2332)", border:"1px solid var(--border)",
          borderRadius:8, maxHeight:320, overflowY:"auto", boxShadow:"0 8px 24px rgba(0,0,0,.4)" }}>
          {results.map((s: any) => (
            <div key={s.symbol} onMouseDown={() => pick(s.symbol)}
              style={{ padding:"9px 14px", cursor:"pointer", display:"flex", alignItems:"center", gap:10,
                borderBottom:"1px solid var(--border-light,#1e2d42)", transition:"background 0.1s" }}
              onMouseEnter={e => (e.currentTarget.style.background="var(--bg-elevated,#1e2d42)")}
              onMouseLeave={e => (e.currentTarget.style.background="transparent")}>
              <span style={{ fontSize:16 }}>{FLAG[s.exchange]||"🌐"}</span>
              <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, fontSize:14, minWidth:60, color:"var(--accent)" }}>{s.symbol}</span>
              <span style={{ fontSize:12, color:"var(--text-muted)", flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{s.name}</span>
              <span style={{ fontSize:10, fontWeight:600, padding:"2px 6px", borderRadius:4,
                background: s.exchange==="SET"?"#0d4f3c":"#1a2c5e",
                color: s.exchange==="SET"?"#00e676":"#7eb3ff" }}>{s.exchange}</span>
            </div>
          ))}
        </div>
      )}
      {open && !loading && results.length===0 && q.trim() && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, zIndex:999,
          background:"var(--bg-surface,#1a2332)", border:"1px solid var(--border)",
          borderRadius:8, padding:"12px 14px", fontSize:13, color:"var(--text-muted)" }}>
          ไม่พบ "{q}" ในระบบ
        </div>
      )}
    </div>
  )
}

const CHART_OPTS = (h: number) => ({
  height: h,
  layout: { background: { color: "#111827" }, textColor: "#7a90a8" },
  grid:   { vertLines: { color:"#1e2d42" }, horzLines: { color:"#1e2d42" } },
  rightPriceScale: { borderColor:"#1e2d42", scaleMarginTop: 0.05, scaleMarginBottom: 0.05 },
  timeScale: { borderColor:"#1e2d42", timeVisible:true, secondsVisible:false, rightOffset:5 },
  crosshair: { mode: 1 },
})

// ── Main Chart ────────────────────────────────────────────────────────────────
export default function Chart({ symbol: initSymbol }: { symbol?: string | null }) {
  const [symbol, setSymbol]   = useState(initSymbol || "")
  const [prices, setPrices]   = useState<PriceData[]>([])
  const [indicators, setInds] = useState<IndicatorData[]>([])
  const [loading, setLoading] = useState(false)
  const [noData,  setNoData]  = useState(false)
  const [days, setDays]       = useState("365")
  const [showEMA, setShowEMA] = useState(true)
  const [showBB,  setShowBB]  = useState(false)
  const [showVol, setShowVol] = useState(true)
  const [showMACD,setShowMACD]= useState(false)

  // chart refs — main + volume + MACD
  const mainRef = useRef<HTMLDivElement>(null)
  const volRef  = useRef<HTMLDivElement>(null)
  const macdRef = useRef<HTMLDivElement>(null)

  const mainChart = useRef<IChartApi|null>(null)
  const volChart  = useRef<IChartApi|null>(null)
  const macdChart = useRef<IChartApi|null>(null)

  const series    = useRef<Record<string, ISeriesApi<any>>>({})
  const ready     = useRef(false)
  const symRef    = useRef(symbol)
  const daysRef   = useRef(days)
  const emaRef    = useRef(showEMA)
  const bbRef     = useRef(showBB)
  const volRef2   = useRef(showVol)
  const macdRef2  = useRef(showMACD)

  useEffect(() => { symRef.current   = symbol   }, [symbol])
  useEffect(() => { daysRef.current  = days     }, [days])
  useEffect(() => { emaRef.current   = showEMA  }, [showEMA])
  useEffect(() => { bbRef.current    = showBB   }, [showBB])
  useEffect(() => { volRef2.current  = showVol  }, [showVol])
  useEffect(() => { macdRef2.current = showMACD }, [showMACD])

  const toLine = (arr: any[], key: string) =>
    arr.filter(i => i[key] != null).map(i => ({ time: i.date, value: parseFloat(i[key]) }))

  // ── fetch + draw ─────────────────────────────────────────────────────────
  const fetchAndDraw = useCallback(async (sym: string, d: string) => {
    if (!sym || !ready.current || !mainChart.current) return
    setLoading(true); setNoData(false)
    try {
      const [pd, id] = await Promise.all([
        api.getPrices(sym, parseInt(d)),
        api.getIndicators(sym, parseInt(d)),
      ])
      const pa = (Array.isArray(pd) ? pd : (pd as any).results || []).slice().reverse()
      const ia = (Array.isArray(id) ? id : (id as any).results || []).slice().reverse()

      if (pa.length === 0) { setNoData(true); setLoading(false); return }
      setPrices(pa); setInds(ia)

      const s = series.current

      // ── Candlestick ──
      s.candle?.setData(pa.map((p: PriceData) => ({
        time: p.date,
        open:  parseFloat(p.open  as any),
        high:  parseFloat(p.high  as any),
        low:   parseFloat(p.low   as any),
        close: parseFloat(p.close as any),
      })))

      // ── EMA / BB ──
      s.ema20?.setData(emaRef.current  ? toLine(ia,"ema20")    : [])
      s.ema50?.setData(emaRef.current  ? toLine(ia,"ema50")    : [])
      s.ema200?.setData(emaRef.current ? toLine(ia,"ema200")   : [])
      s.bbU?.setData(bbRef.current     ? toLine(ia,"bb_upper") : [])
      s.bbL?.setData(bbRef.current     ? toLine(ia,"bb_lower") : [])

      // ── Volume histogram ──
      if (volRef2.current && s.vol) {
        s.vol.setData(pa.map((p: PriceData) => ({
          time:  p.date,
          value: Number(p.volume),
          color: parseFloat(p.close as any) >= parseFloat(p.open as any)
            ? "rgba(0,230,118,.5)" : "rgba(255,82,82,.5)",
        })))
        volChart.current?.timeScale().fitContent()
      }

      // ── MACD ──
      if (macdRef2.current && ia.length > 0) {
        const macdLine   = toLine(ia, "macd")
        const signalLine = toLine(ia, "macd_signal")
        const histData   = ia.filter(i => i.macd_hist != null).map(i => ({
          time:  i.date,
          value: parseFloat(i.macd_hist),
          color: parseFloat(i.macd_hist) >= 0 ? "rgba(0,230,118,.7)" : "rgba(255,82,82,.7)",
        }))
        s.macdLine?.setData(macdLine)
        s.macdSignal?.setData(signalLine)
        s.macdHist?.setData(histData)
        macdChart.current?.timeScale().fitContent()
      }

      // fit main
      mainChart.current.timeScale().fitContent()
      if (mainRef.current)
        mainChart.current.applyOptions({ width: mainRef.current.clientWidth })

    } catch (e) { console.error("Chart:", e) }
    setLoading(false)
  }, [])

  // ── init charts ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mainRef.current || mainChart.current) return

    const init = () => {
      if (!mainRef.current) return
      const w = mainRef.current.clientWidth || 800

      // Main chart
      mainChart.current = createChart(mainRef.current, { ...CHART_OPTS(420), width: w })
      const mc = mainChart.current
      series.current = {
        candle: mc.addSeries(CandlestickSeries, {
          upColor:"#00e676", downColor:"#ff5252",
          borderVisible:false, wickUpColor:"#00e676", wickDownColor:"#ff5252"
        }),
        ema20:  mc.addSeries(LineSeries, { color:"#00d4ff", lineWidth:1, title:"EMA20" }),
        ema50:  mc.addSeries(LineSeries, { color:"#ffd740", lineWidth:1, title:"EMA50" }),
        ema200: mc.addSeries(LineSeries, { color:"#ff5252", lineWidth:2, title:"EMA200" }),
        bbU:    mc.addSeries(LineSeries, { color:"rgba(100,100,255,.5)", lineWidth:1, lineStyle:2 }),
        bbL:    mc.addSeries(LineSeries, { color:"rgba(100,100,255,.5)", lineWidth:1, lineStyle:2 }),
      }

      // Volume chart
      if (volRef.current) {
        volChart.current = createChart(volRef.current, {
          ...CHART_OPTS(100), width: w,
          timeScale: { visible: false },
          rightPriceScale: { borderColor:"#1e2d42", scaleMarginTop:0.1, scaleMarginBottom:0 },
        })
        series.current.vol = volChart.current.addSeries(HistogramSeries, {
          priceFormat: { type:"volume" }, priceScaleId:"volume",
        })
        volChart.current.priceScale("volume").applyOptions({ scaleMarginTop:0.1, scaleMarginBottom:0 })
      }

      // MACD chart
      if (macdRef.current) {
        macdChart.current = createChart(macdRef.current, {
          ...CHART_OPTS(120), width: w,
          timeScale: { visible: false },
        })
        const macc = macdChart.current
        series.current.macdHist   = macc.addSeries(HistogramSeries, { color:"rgba(0,212,255,.6)", title:"MACD Hist" })
        series.current.macdLine   = macc.addSeries(LineSeries, { color:"#00d4ff", lineWidth:1, title:"MACD" })
        series.current.macdSignal = macc.addSeries(LineSeries, { color:"#ffd740", lineWidth:1, title:"Signal" })
      }

      // Sync crosshair between all charts
      const syncCross = (src: IChartApi, targets: IChartApi[]) => {
        src.subscribeCrosshairMove(p => {
          const t = (p.time as any)
          targets.forEach(tc => {
            if (t) tc.setCrossHairPosition(p.point?.x ?? 0, p.point?.y ?? 0, tc.series?.()[0])
            else tc.clearCrossHairPosition()
          })
        })
      }
      const all = [mainChart.current, volChart.current, macdChart.current].filter(Boolean) as IChartApi[]
      all.forEach(c => syncCross(c, all.filter(o => o !== c)))

      const ro = new ResizeObserver(() => {
        const cw = mainRef.current?.clientWidth || 0
        mainChart.current?.applyOptions({ width: cw })
        volChart.current?.applyOptions({ width: cw })
        macdChart.current?.applyOptions({ width: cw })
      })
      ro.observe(mainRef.current)
      ready.current = true

      if (symRef.current) fetchAndDraw(symRef.current, daysRef.current)

      return () => {
        ready.current = false
        mainChart.current?.remove(); mainChart.current = null
        volChart.current?.remove();  volChart.current  = null
        macdChart.current?.remove(); macdChart.current = null
        ro.disconnect()
      }
    }

    const raf = requestAnimationFrame(init)
    return () => cancelAnimationFrame(raf)
  }, [fetchAndDraw])

  // sync initSymbol
  useEffect(() => {
    if (initSymbol && initSymbol !== symRef.current) {
      setSymbol(initSymbol); symRef.current = initSymbol
      if (ready.current) fetchAndDraw(initSymbol, daysRef.current)
    }
  }, [initSymbol, fetchAndDraw])

  function handleSelect(sym: string) { setSymbol(sym); symRef.current = sym; fetchAndDraw(sym, daysRef.current) }
  function handleDays(d: string)     { setDays(d); daysRef.current = d; if (symRef.current) fetchAndDraw(symRef.current, d) }
  function toggle(ref: React.MutableRefObject<boolean>, fn: (v:boolean)=>void) {
    const n = !ref.current; ref.current = n; fn(n)
    if (symRef.current) fetchAndDraw(symRef.current, daysRef.current)
  }

  const lp  = prices[prices.length-1]
  const pp  = prices[prices.length-2]
  const li  = indicators[indicators.length-1]
  const chg = lp && pp ? parseFloat(lp.close as any) - parseFloat(pp.close as any) : 0
  const pct = pp && parseFloat(pp.close as any) ? (chg/parseFloat(pp.close as any))*100 : 0
  const up  = chg >= 0

  const TF = [
    {label:"3 เดือน",v:"90"},{label:"6 เดือน",v:"180"},
    {label:"1 ปี",v:"365"},{label:"2 ปี",v:"730"},{label:"5 ปี",v:"1825"},
  ]
  const TOGGLES = [
    {label:"EMA",  color:"#00d4ff", val:showEMA,  fn:()=>toggle(emaRef,  setShowEMA)},
    {label:"BB",   color:"#6464ff", val:showBB,   fn:()=>toggle(bbRef,   setShowBB)},
    {label:"VOL",  color:"#69f0ae", val:showVol,  fn:()=>toggle(volRef2, setShowVol)},
    {label:"MACD", color:"#ffd740", val:showMACD, fn:()=>toggle(macdRef2,setShowMACD)},
  ]

  return (
    <div className="fade-up">
      <div className="page-header">
        <div className="page-title">📈 กราฟราคา</div>
        <div className="page-subtitle">ค้นหาหุ้นได้ทุกตลาด · SET · NYSE · NASDAQ</div>
      </div>
      <div className="page-body">

        {/* Controls */}
        <div className="card" style={{ marginBottom:16 }}>
          <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"center" }}>
            <SymbolSearch onSelect={handleSelect} />
            <div style={{ display:"flex", gap:4 }}>
              {TF.map(tf => (
                <button key={tf.v} onClick={() => handleDays(tf.v)} style={{
                  padding:"6px 12px", borderRadius:6, fontSize:12, fontWeight:600, cursor:"pointer",
                  border:`1px solid ${days===tf.v?"var(--accent)":"var(--border)"}`,
                  background: days===tf.v?"var(--accent-dim)":"transparent",
                  color: days===tf.v?"var(--accent)":"var(--text-secondary)", transition:"all .15s",
                }}>{tf.label}</button>
              ))}
            </div>
            <div style={{ display:"flex", gap:6, marginLeft:"auto" }}>
              {TOGGLES.map(({ label, color, val, fn }) => (
                <button key={label} onClick={fn} style={{
                  padding:"6px 12px", borderRadius:6, fontSize:12, fontWeight:600, cursor:"pointer",
                  border:`1px solid ${val?color:"var(--border)"}`,
                  background: val?`${color}22`:"transparent",
                  color: val?color:"var(--text-muted)",
                }}><AiTerm token={label}>{label}</AiTerm></button>
              ))}
            </div>
          </div>
        </div>

        {/* Price Info Bar */}
        {lp && (
          <div style={{ display:"flex", gap:16, marginBottom:14, alignItems:"center", flexWrap:"wrap" }}>
            <span style={{ fontFamily:"var(--font-mono)", fontSize:26, fontWeight:700 }}>{symbol}</span>
            <span style={{ fontFamily:"var(--font-mono)", fontSize:22, fontWeight:700, color:up?"var(--green)":"var(--red)" }}>
              {parseFloat(lp.close as any).toLocaleString("th-TH",{minimumFractionDigits:2})}
            </span>
            <span style={{ fontSize:14, color:up?"var(--green)":"var(--red)" }}>
              {up?"▲":"▼"} {Math.abs(chg).toFixed(2)} ({Math.abs(pct).toFixed(2)}%)
            </span>
            {li && (
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                {[
                  {l:"RSI",  v:li.rsi,        d:1, c: parseFloat(li.rsi as any)<30?"var(--blue)":parseFloat(li.rsi as any)>70?"var(--yellow)":"var(--green)"},
                  {l:"MACD", v:li.macd,        d:3, c:"var(--accent)"},
                  {l:"EMA20",v:li.ema20,       d:2, c:"#00d4ff"},
                  {l:"ADX",  v:(li as any).adx14, d:1, c:"var(--text-primary)"},
                ].filter(x=>x.v!=null).map(({l,v,d,c}) => (
                  <div key={l} style={{ background:"var(--bg-elevated)", border:"1px solid var(--border)", borderRadius:6, padding:"4px 10px", fontSize:12 }}>
                    <span style={{ color:"var(--text-muted)" }}><AiTerm token={l}>{l}</AiTerm></span>{" "}
                    <span style={{ fontFamily:"var(--font-mono)", fontWeight:700, color:c }}>
                      {parseFloat(v as any).toFixed(d)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Chart Area */}
        <div className="card" style={{ padding:0, overflow:"hidden", position:"relative" }}>
          {loading && (
            <div style={{ position:"absolute", inset:0, zIndex:10, display:"flex",
              alignItems:"center", justifyContent:"center", background:"rgba(17,24,39,.7)" }}>
              <div className="loading-spinner" />
            </div>
          )}

          {/* Main candlestick */}
          <div ref={mainRef} style={{ width:"100%", height:420 }} />

          {/* Volume sub-panel */}
          <div ref={volRef} style={{
            width:"100%", height: showVol ? 100 : 0,
            borderTop: showVol ? "1px solid #1e2d42" : "none",
            overflow:"hidden", transition:"height .2s"
          }} />

          {/* MACD sub-panel */}
          <div style={{ display:"flex", alignItems:"center", padding: showMACD?"4px 12px":"0",
            height: showMACD ? undefined : 0, overflow:"hidden" }}>
            {showMACD && <span style={{ fontSize:10, color:"var(--text-muted)", marginRight:8, flexShrink:0 }}>MACD</span>}
            <div ref={macdRef} style={{
              flex:1, height: showMACD ? 120 : 0,
              borderTop: showMACD ? "1px solid #1e2d42" : "none",
              overflow:"hidden", transition:"height .2s"
            }} />
          </div>

          {/* Overlay: ยังไม่เลือกหุ้น */}
          {!symbol && !loading && (
            <div style={{ position:"absolute", inset:0, background:"#111827",
              display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:12 }}>
              <span style={{ fontSize:48 }}>📈</span>
              <span style={{ fontWeight:600, color:"var(--text-primary)" }}>ค้นหาหุ้นที่ต้องการดูกราฟ</span>
              <span style={{ fontSize:12, color:"var(--text-muted)" }}>🇹🇭 SET · 🇺🇸 NYSE · NASDAQ</span>
            </div>
          )}
          {symbol && noData && !loading && (
            <div style={{ position:"absolute", inset:0, background:"#111827",
              display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:12 }}>
              <span style={{ fontSize:48 }}>📭</span>
              <span style={{ fontWeight:600, color:"var(--text-primary)" }}>ไม่มีข้อมูลราคาสำหรับ {symbol}</span>
            </div>
          )}
        </div>

        {/* RSI Bar */}
        {li && (
          <div className="card" style={{ marginTop:14 }}>
            <div className="card-title"><TermText text="RSI 14" /></div>
            <div style={{ display:"flex", alignItems:"center", gap:16 }}>
              <div style={{ flex:1, height:8, background:"var(--border)", borderRadius:4, position:"relative" }}>
                <div style={{
                  position:"absolute", top:"50%", transform:"translate(-50%,-50%)",
                  left:`${Math.min(parseFloat(li.rsi as any||"50"),100)}%`,
                  width:14, height:14, borderRadius:"50%",
                  background: parseFloat(li.rsi as any)<30?"var(--blue)":parseFloat(li.rsi as any)>70?"var(--yellow)":"var(--green)",
                  border:"2px solid var(--bg-surface)",
                }} />
                <div style={{ position:"absolute", left:"30%", top:0, bottom:0, width:1, background:"var(--blue)", opacity:.4 }} />
                <div style={{ position:"absolute", left:"70%", top:0, bottom:0, width:1, background:"var(--yellow)", opacity:.4 }} />
              </div>
              <span style={{ fontFamily:"var(--font-mono)", fontSize:20, fontWeight:700,
                color: parseFloat(li.rsi as any)<30?"var(--blue)":parseFloat(li.rsi as any)>70?"var(--yellow)":"var(--green)" }}>
                {parseFloat(li.rsi as any||"0").toFixed(1)}
              </span>
              <span style={{ fontSize:12, color:"var(--text-secondary)" }}>
                {parseFloat(li.rsi as any)<30?"🔵 Oversold":parseFloat(li.rsi as any)>70?"🟡 Overbought":"✅ ปกติ"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
