import { API_BASE } from "./config"
import {
  DashboardResponse,
  SymbolInfo,
  PriceData,
  IndicatorData,
  SignalInfo,
  ScannerResult,
  UserInfo,
  BusinessProfileInfo,
  StockTermInfo,
  ChatMessageInfo,
  ChatConversation,
} from "./types"

const BASE_URL = API_BASE

function getAuthHeader() {
  const token = localStorage.getItem("sr_token")
  return token ? { Authorization: `Token ${token}` } : {}
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`
  const headers = new Headers(options.headers)
  headers.set("Content-Type", "application/json")
  const auth = getAuthHeader()
  if (auth.Authorization) headers.set("Authorization", auth.Authorization)

  const res = await fetch(url, {
    headers,
    ...options,
  })
  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem("sr_token")
      window.location.reload()
    }
    throw new Error(`API Error ${res.status}: ${url}`)
  }
  return res.json()
}

export const api = {
  getProfile: (): Promise<UserInfo> => apiFetch("/profile/"),
  getBusinessProfile: (): Promise<BusinessProfileInfo> => apiFetch("/business-profile/"),
  getTerm: (q: string): Promise<StockTermInfo> =>
    apiFetch("/term/?" + new URLSearchParams({ q })),
  searchTerms: (q: string): Promise<{ results: StockTermInfo[] }> =>
    apiFetch("/terms/search/?" + new URLSearchParams({ q })),
  getFeaturedTerms: (): Promise<{ results: StockTermInfo[] }> =>
    apiFetch("/terms/featured/"),
  updateProfile: (data: Partial<UserInfo["profile"]>): Promise<UserInfo> =>
    apiFetch("/profile/", {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  login: (credentials: any): Promise<{ key: string }> =>
    apiFetch("/auth/login/", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
  logout: (): Promise<any> =>
    apiFetch("/auth/logout/", {
      method: "POST",
    }),
  getDashboard: (): Promise<DashboardResponse> => apiFetch("/dashboard/"),
  getSymbols: (params: Record<string, string> = {}): Promise<{ results: SymbolInfo[] }> =>
    apiFetch("/symbols/?" + new URLSearchParams(params)),
  getPrices: (symbol: string, days = 365): Promise<PriceData[]> =>
    apiFetch(`/prices/${symbol}/?days=${days}`),
  getIndicators: (symbol: string, days = 100): Promise<IndicatorData[]> =>
    apiFetch(`/indicators/${symbol}/?days=${days}`),
  getSignals: (params: Record<string, string> = {}): Promise<{ results: SignalInfo[] }> =>
    apiFetch("/signals/?" + new URLSearchParams(params)),
  getScanner: (params: Record<string, string> = {}): Promise<{ count: number; results: ScannerResult[] }> =>
    apiFetch("/scanner/?" + new URLSearchParams(params)),
  runScanner: (exchange: string): Promise<{ status: string; result: any }> =>
    apiFetch("/scanner/run/", {
      method: "POST",
      body: JSON.stringify({ exchange }),
    }),
  runBacktest: (body: any): Promise<any> =>
    apiFetch("/backtest/", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  // ── Multi-Layer Scanner ───────────────────────────────────────────────────
  getMultiLayer: (params: Record<string, string> = {}): Promise<{ count: number; results: any[] }> =>
    apiFetch("/multi-layer/?" + new URLSearchParams(params)),

  // ── Chat ──────────────────────────────────────────────────────────────────
  chatSend: (body: string, receiver_id?: number): Promise<ChatMessageInfo> =>
    apiFetch("/chat/send/", {
      method: "POST",
      body: JSON.stringify({ body, ...(receiver_id ? { receiver_id } : {}) }),
    }),
  chatMessages: (user_id?: number): Promise<{ messages: ChatMessageInfo[] }> =>
    apiFetch("/chat/messages/" + (user_id ? `?user_id=${user_id}` : "")),
  chatConversations: (): Promise<{ conversations: ChatConversation[] }> =>
    apiFetch("/chat/conversations/"),

  // ── Alpaca ────────────────────────────────────────────────────────────────
  alpacaConfirmOrder: (orderId: number): Promise<any> =>
    apiFetch(`/alpaca/orders/${orderId}/confirm/`, { method: "POST", body: JSON.stringify({}) }),
  alpacaCancelOrder: (orderId: number): Promise<any> =>
    apiFetch(`/alpaca/orders/${orderId}/cancel/`, { method: "POST", body: JSON.stringify({}) }),
  alpacaAccount: (): Promise<any> =>
    apiFetch("/alpaca/account/"),
  alpacaPositions: (): Promise<any[]> =>
    apiFetch("/alpaca/positions/").then((r: any) => r.positions ?? r ?? []),
  alpacaOrders: (status = "all", limit = 20): Promise<any[]> =>
    apiFetch(`/alpaca/orders/?status=${status}&limit=${limit}`).then((r: any) => r.orders ?? r ?? []),
  alpacaPortfolioHistory: (period = "1M", timeframe = "1D"): Promise<any> =>
    apiFetch(`/alpaca/portfolio/?period=${period}&timeframe=${timeframe}`),
  alpacaClock: (): Promise<any> =>
    apiFetch("/alpaca/clock/"),
}
