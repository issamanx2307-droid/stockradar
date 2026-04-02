"""
URL Routes สำหรับ Radar หุ้น API
"""

from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/",               views.dashboard_summary,            name="dashboard"),
    path("profile/",                 views.user_profile,                 name="profile"),
    path("business-profile/",        views.business_profile_api,         name="business-profile"),
    path("term/",                    views.term_lookup,                  name="term-lookup"),
    path("terms/search/",            views.term_search,                  name="term-search"),
    path("terms/featured/",          views.featured_terms,               name="term-featured"),
    path("position/analyze/",        views.position_analyze_api,         name="position-analyze"),
    path("symbols/",                 views.SymbolListView.as_view(),      name="symbol-list"),
    path("prices/<str:symbol>/",     views.PriceListView.as_view(),       name="price-list"),
    path("indicators/<str:symbol>/", views.IndicatorListView.as_view(),   name="indicator-list"),
    path("signals/",                 views.SignalListView.as_view(),       name="signal-list"),
    path("scanner/",                 views.scanner_view,                   name="scanner"),
    path("scanner/run/",             views.run_scanner_api,                name="scanner-run"),
    path("backtest/",                views.run_backtest_api,               name="backtest"),
    path("cache/stats/",             views.cache_stats,                    name="cache-stats"),
    path("cache/warmup/",            views.cache_warmup,                   name="cache-warmup"),
    path("cache/invalidate/",        views.cache_invalidate,               name="cache-invalidate"),
    path("news/",                    views.news_list,                      name="news-list"),
    path("news/fetch/",              views.news_fetch,                     name="news-fetch"),
    path("news/sentiment/",          views.news_sentiment_summary,         name="news-sentiment"),
    # ── Watchlist & Personal Portfolio ──
    path("watchlist/",                          views.watchlist_list,            name="watchlist-list"),
    path("watchlist/add/",                      views.watchlist_add_item,        name="watchlist-add"),
    path("watchlist/item/<int:item_id>/",       views.watchlist_remove_item,     name="watchlist-remove"),
    path("watchlist/item/<int:item_id>/trade/", views.watchlist_add_trade,       name="watchlist-trade"),
    path("watchlist/trade/<int:trade_id>/",    views.watchlist_delete_trade,     name="watchlist-trade-delete"),
    path("watchlist/item/<int:item_id>/calc-sell/", views.watchlist_calc_sell,   name="watchlist-calc"),
    path("watchlist/item/<int:item_id>/alert/", views.watchlist_update_alert,    name="watchlist-alert"),
    path("watchlist/history/",                  views.watchlist_portfolio_history, name="watchlist-history"),
    # ── Fundamental Data ──
    path("fundamental/batch/",         views.fundamental_batch,  name="fundamental-batch"),
    path("fundamental/<str:symbol>/",  views.fundamental_data,   name="fundamental"),
    # ── Ticker Tape ──
    path("ticker/",                    views.ticker_tape,           name="ticker"),
    path("calendar/",                  views.economic_calendar_api, name="calendar"),
    path("thai-indicators/",           views.thai_indicators_api,   name="thai-indicators"),
    path("subscription/",              views.subscription_status,   name="subscription"),
    path("subscription/plans/",        views.subscription_plans,    name="subscription-plans"),
    # ── GitHub Actions Data Import ──
    path("symbols-export/",            views.symbols_export,        name="symbols-export"),
    path("import-prices/",             views.import_prices,         name="import-prices"),
    # ── Latest Snapshot (Materialized View) ──
    path("snapshot/",                  views.latest_snapshot,       name="latest-snapshot"),
    # ── Engine Trigger ──
    path("trigger-engine/",            views.trigger_engine),
    # ── Admin API ──
    path("admin/stats/",               views.admin_stats,            name="admin-stats"),
    path("admin/fetch-news/",          views.admin_fetch_news,       name="admin-fetch-news"),
    path("admin/refresh-snapshot/",    views.admin_refresh_snapshot, name="admin-refresh-snapshot"),
    # ── VI Screener ──
    path("vi-screen/",                 views.vi_screen_api,          name="vi-screen"),
    # ── Chat System ──
    path("chat/send/",                 views.chat_send,              name="chat-send"),
    path("chat/messages/",             views.chat_messages,          name="chat-messages"),
    path("chat/conversations/",        views.chat_conversations,     name="chat-conversations"),
]
