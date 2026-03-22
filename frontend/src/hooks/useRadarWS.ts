/**
 * useRadarWS — React hook สำหรับ WebSocket connection
 */
import { useState, useEffect, useRef, useCallback } from "react"
import { SignalInfo } from "../api/types"

const getWsUrl = () => {
  // Production: ใช้ wss:// กับ hostname เดียวกัน (Vite proxy จะ forward /ws → backend)
  // Development: ใช้ port 8000 โดยตรง
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
  const host = window.location.hostname
  const port = window.location.port
  // ถ้า port คือ 5173 = dev, ใช้ 8000 แทน (Vite proxy ws)
  if (port === "5173") return `${protocol}//${host}:8000/ws/radar/`
  return `${protocol}//${window.location.host}/ws/radar/`
}

const WS_URL = getWsUrl()
const RECONNECT_MS = 3000

export interface RadarWS {
  connected: boolean;
  stats: any;
  signals: SignalInfo[];
  newSignal: SignalInfo | null;
  prices: Record<string, any>;
  scanProgress: any;
  scanDone: any;
  subscribePrice: (syms: string[]) => void;
  requestStats: () => void;
}

export function useRadarWS(): RadarWS {
  const wsRef = useRef<WebSocket | null>(null)
  const timerRef = useRef<any>(null)
  const [connected, setConnected] = useState(false)
  const [stats, setStats] = useState<any>(null)
  const [signals, setSignals] = useState<SignalInfo[]>([])
  const [newSignal, setNewSignal] = useState<SignalInfo | null>(null)
  const [prices, setPrices] = useState<Record<string, any>>({})
  const [scanProgress, setScanProgress] = useState<any>(null)
  const [scanDone, setScanDone] = useState<any>(null)

  const send = useCallback((obj: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(obj))
    }
  }, [])

  const handle = useCallback((msg: any) => {
    if (msg.type === "stats") setStats(msg.data)
    if (msg.type === "signals") setSignals(msg.data || [])
    if (msg.type === "signal_new") {
      setNewSignal(msg.data)
      setSignals(p => [msg.data, ...p].slice(0, 50))
    }
    if (msg.type === "prices") {
      setPrices(p => {
        const n = { ...p };
        (msg.data || []).forEach((x: any) => n[x.symbol] = x)
        return n
      })
    }
    if (msg.type === "scanner_progress") {
      setScanProgress(msg.data)
      setScanDone(null)
    }
    if (msg.type === "scanner_done") {
      setScanDone(msg.data)
      setScanProgress(null)
    }
  }, [])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    try {
      wsRef.current = new WebSocket(WS_URL)
      wsRef.current.onopen = () => {
        setConnected(true)
        clearTimeout(timerRef.current)
      }
      wsRef.current.onclose = () => {
        setConnected(false)
        timerRef.current = setTimeout(connect, RECONNECT_MS)
      }
      wsRef.current.onerror = () => {
        wsRef.current?.close()
      }
      wsRef.current.onmessage = (e) => {
        try {
          handle(JSON.parse(e.data))
        } catch (_) {}
      }
    } catch (_) {
      timerRef.current = setTimeout(connect, RECONNECT_MS)
    }
  }, [handle])

  const subscribePrice = useCallback((syms: string[]) => send({ action: "subscribe_prices", symbols: syms }), [send])
  const requestStats = useCallback(() => send({ action: "get_stats" }), [send])

  useEffect(() => {
    connect()
    const ping = setInterval(() => send({ action: "ping" }), 30000)
    return () => {
      clearInterval(ping)
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect, send])

  return { connected, stats, signals, newSignal, prices, scanProgress, scanDone, subscribePrice, requestStats }
}
