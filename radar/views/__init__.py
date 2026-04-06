"""
radar/views — Views package

Re-exports ทุก view function/class จาก sub-modules
เพื่อให้ urls.py ใช้ from radar.views import xxx ได้เหมือนเดิม
"""

# Dashboard & Profile
from .dashboard import dashboard_summary, user_profile

# Terms & Position Analyze
from .terms import (
    business_profile_api, term_lookup, term_search,
    featured_terms, position_analyze_api,
)

# Scanner, Symbols, Prices, Indicators, Signals, Backtest
from .scanner import (
    SymbolListView, PriceListView, IndicatorListView, SignalListView,
    scanner_view, run_scanner_api, run_backtest_api,
)

# Cache Management
from .cache import cache_stats, cache_warmup, cache_invalidate

# News & Sentiment
from .news import news_list, news_fetch, news_sentiment_summary

# Watchlist & Portfolio
from .watchlist import (
    watchlist_list, watchlist_add_item, watchlist_remove_item,
    watchlist_add_trade, watchlist_delete_trade,
    watchlist_calc_sell, watchlist_update_alert,
    watchlist_portfolio_history,
)

# Fundamental, Ticker, Calendar, Thai Indicators
from .fundamental import (
    fundamental_data, fundamental_batch,
    ticker_tape, economic_calendar_api, thai_indicators_api,
)

# Subscription
from .subscription import subscription_status, subscription_plans

# Data Import, Snapshot, Trigger, Admin
from .data_import import (
    symbols_export, import_prices,
    latest_snapshot, trigger_engine,
    admin_stats, admin_fetch_news, admin_refresh_snapshot,
)

# VI Screener & Multi-Layer
from .vi_screen import vi_screen_api, multi_layer_scan

# Chat System
from .chat import chat_send, chat_messages, chat_conversations

# Alpaca US Trading
from .alpaca import (
    alpaca_account, alpaca_positions, alpaca_orders,
    alpaca_propose_order, alpaca_confirm_order, alpaca_cancel_order,
    alpaca_portfolio, alpaca_market_clock, alpaca_bars,
)
