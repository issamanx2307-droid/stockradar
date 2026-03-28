export interface SymbolInfo {
  id: number;
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
}

export interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorData {
  date: string;
  rsi?: number;
  ema20?: number;
  ema50?: number;
  ema200?: number;
  macd?: number;
  macd_signal?: number;
  macd_hist?: number;
  atr14?: number;
  adx14?: number;
}

export interface SignalInfo {
  id: number;
  symbol_code: string;
  symbol_name: string;
  exchange: string;
  signal_type: string;
  signal_display: string;
  direction: string;
  direction_display: string;
  score: number;
  price: number;
  stop_loss?: number;
  risk_pct?: number;
  atr_at_signal?: number;
  adx_at_signal?: number;
  volume_ratio?: number;
  filter_volume?: boolean;
  filter_volatility?: boolean;
  filter_adx?: boolean;
  created_at: string;
}

export interface ScannerResult {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  close: number;
  score: number;
  direction: string;
  signal_type: string;
  rsi?: number;
  adx14?: number;
  stop_loss?: number;
}

export interface DashboardStats {
  total_symbols: number;
  total_signals: number;
  buy_signals: number;
  sell_signals: number;
  breakout_count: number;
  strong_signals: number;
}

export interface ProfileInfo {
  tier: "FREE" | "PRO" | "PREMIUM";
  line_notify_token?: string;
  telegram_chat_id?: string;
  max_strategies: number;
  is_pro: boolean;
  picture_url?: string;
  login_via_google?: boolean;
}

export interface UserInfo {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  profile: ProfileInfo;
}

export interface BusinessProfileInfo {
  company_name: string;
  description: string;
  address: string;
  phone: string;
  email: string;
  line_id: string;
  facebook_url: string;
  website_url: string;
  footer_text: string;
}

export interface StockTermInfo {
  term: string;
  short_definition: string;
  full_definition: string;
  category: string;
  keywords: string[];
  is_featured: boolean;
  priority: number;
  updated_at: string;
}

export interface TermQuestionTicket {
  id: number;
  question: string;
  normalized_term: string;
  status: "NEW" | "ANSWERED";
  answer_short: string;
  answer_full: string;
  answered_at: string | null;
  asked_by_username: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardResponse {
  stats: DashboardStats;
  latest_signals: SignalInfo[];
  top_bullish: SignalInfo[];
}

export interface ChatMessageInfo {
  id: number;
  body: string;
  sender_id: number;
  sender: string;
  is_mine: boolean;
  is_admin_msg: boolean;
  is_read: boolean;
  created_at: string;
}

export interface ChatConversation {
  user_id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  unread: number;
  last_body: string;
  last_at: string | null;
}
