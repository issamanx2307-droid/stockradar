/**
 * frontend/src/api/engineApi.ts
 * Client สำหรับ Engine API ใหม่ (/engine/...)
 */

import { API_BASE } from "./config"
const BASE = API_BASE.replace("/api", "")
const ENGINE = `${BASE}/engine`

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem("sr_token")
  return token ? { Authorization: `Token ${token}` } : {}
}

async function engineFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${ENGINE}${path}`, {
    headers: { "Content-Type": "application/json", ...getAuthHeader() },
    ...options,
  })
  if (!res.ok) throw new Error(`Engine API ${res.status}: ${path}`)
  return res.json()
}

export interface EngineScore {
  total_score: number
  breakdown: {
    trend: number
    momentum: number
    volume: number
    volatility: number
    risk_penalty: number
  }
}

export interface EngineResult {
  symbol: string
  score: number
  breakdown: EngineScore["breakdown"]
  decision: "STRONG BUY" | "BUY" | "HOLD" | "WATCH" | "SELL"
  reasons: string[]
  entry: number
  stop_loss: number
  risk_pct: number
  size?: number
  rsi?: number
  adx?: number
}

export interface BacktestResult {
  symbol: string
  equity_curve: number[]
  metrics: {
    total_return: number
    win_rate: number
    max_drawdown: number
    sharpe: number
    profit_factor: number
    total_trades: number
    winning_trades: number
    final_equity: number
  }
  report: Record<string, string | number>
}

export const engineApi = {
  scan: (params: { exchange?: string; top?: number; min_score?: number } = {}) =>
    engineFetch<{ count: number; results: EngineResult[] }>(
      `/scan/?${new URLSearchParams(params as any)}`
    ),

  analyze: (symbol: string, capital = 100_000) =>
    engineFetch<EngineResult>(`/analyze/${symbol}/?capital=${capital}`),

  backtest: (body: {
    symbol: string; capital?: number
    stop_loss_pct?: number; take_profit_pct?: number; days?: number
  }) =>
    engineFetch<BacktestResult>("/backtest/", { method: "POST", body: JSON.stringify(body) }),

  portfolio: (body: { capital: number; exchange?: string; min_score?: number }) =>
    engineFetch<{ summary: any; decisions: any[] }>(
      "/portfolio/run/", { method: "POST", body: JSON.stringify(body) }
    ),
}
