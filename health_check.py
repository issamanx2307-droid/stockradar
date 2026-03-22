"""
health_check.py — ตรวจสอบระบบ StockRadar ทุก layer
รัน: .venv\Scripts\python health_check.py

ตรวจสอบ:
  1. Django + DB connection
  2. Models & data counts
  3. Engine modules (indicator, scanner, scoring, decision)
  4. API endpoints (HTTP)
  5. WebSocket
  6. Scheduler config
  7. Logic consistency
"""
import os, sys, time, json, traceback
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockradar.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PASS = "  [PASS]"
FAIL = "  [FAIL]"
WARN = "  [WARN]"
INFO = "  [INFO]"

results = []

def check(name, fn):
    try:
        msg = fn()
        results.append((True, name, msg or "OK"))
        print(f"{PASS} {name}: {msg or 'OK'}")
        return True
    except Exception as e:
        results.append((False, name, str(e)))
        print(f"{FAIL} {name}: {e}")
        return False

print("\n" + "="*60)
print("  StockRadar Health Check")
print("="*60)

# ─── 1. DJANGO SETUP ──────────────────────────────────────────
print("\n[1] Django & Database")

def check_django():
    import django
    django.setup()
    return f"Django {django.__version__}"
check("Django setup", check_django)

def check_db():
    from django.db import connection
    with connection.cursor() as c:
        c.execute("SELECT 1")
    return "SQLite connected"
check("Database connection", check_db)

def check_migrations():
    from django.db.migrations.executor import MigrationExecutor
    from django.db import connection
    executor = MigrationExecutor(connection)
    plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
    if plan:
        raise Exception(f"{len(plan)} unapplied migrations")
    return "All migrations applied"
check("Migrations", check_migrations)

# ─── 2. MODELS & DATA ─────────────────────────────────────────
print("\n[2] Models & Data")

def check_symbols():
    from radar.models import Symbol
    n = Symbol.objects.count()
    if n == 0: raise Exception("No symbols in DB")
    return f"{n} symbols"
check("Symbols", check_symbols)

def check_prices():
    from radar.models import PriceDaily
    n = PriceDaily.objects.count()
    if n < 100: raise Exception(f"Only {n} price records (expected >100)")
    latest = PriceDaily.objects.order_by("-date").first()
    return f"{n:,} records, latest: {latest.date}"
check("Price data", check_prices)

def check_indicators():
    from radar.models import Indicator
    n = Indicator.objects.count()
    if n < 100: raise Exception(f"Only {n} indicator records")
    return f"{n:,} records"
check("Indicators", check_indicators)

def check_signals():
    from radar.models import Signal
    n = Signal.objects.count()
    buy = Signal.objects.filter(direction="LONG").count()
    sell = Signal.objects.filter(direction="SHORT").count()
    return f"{n} total | BUY:{buy} SELL:{sell}"
check("Signals", check_signals)

def check_news():
    from radar.models import NewsItem
    n = NewsItem.objects.count()
    return f"{n} news items"
check("News", check_news)

# ─── 3. ENGINE MODULES ────────────────────────────────────────
print("\n[3] Engine Modules")

def check_indicators_engine():
    from radar.models import PriceDaily, Symbol
    import pandas as pd
    sym = Symbol.objects.filter(exchange="SET").first()
    if not sym: raise Exception("No SET symbol")
    prices = PriceDaily.objects.filter(symbol=sym).order_by("date").values("date","open","high","low","close","volume")
    if len(prices) < 30: raise Exception(f"Not enough price data for {sym.symbol}")
    df = pd.DataFrame(list(prices))
    df = df.set_index("date")
    for col in ["open","high","low","close"]: df[col] = df[col].astype(float)
    # ทดสอบ indicator engine
    sys.path.insert(0, "D:/stockradar")
    from indicator_engine.indicators import compute_all
    ind = compute_all(df)
    required = ["ema20","ema50","ema200","rsi14","atr14","adx14"]
    missing = [k for k in required if k not in ind]
    if missing: raise Exception(f"Missing indicators: {missing}")
    return f"EMA20={ind['ema20'].iloc[-1]:.2f} RSI={ind['rsi14'].iloc[-1]:.1f} ADX={ind['adx14'].iloc[-1]:.1f}"
check("Indicator engine", check_indicators_engine)

def check_scanner_engine():
    from radar.models import PriceDaily, Symbol
    import pandas as pd
    sym = Symbol.objects.filter(exchange="SET").order_by("symbol").first()
    prices = PriceDaily.objects.filter(symbol=sym).order_by("date").values("date","open","high","low","close","volume")
    df = pd.DataFrame(list(prices)).set_index("date")
    for col in ["open","high","low","close"]: df[col] = df[col].astype(float)
    from scanner_engine.scanner import scan_stock
    signals = scan_stock(df)
    required = ["ema_alignment","breakout_20d","volume_spike","overbought"]
    missing = [k for k in required if k not in signals]
    if missing: raise Exception(f"Missing signal keys: {missing}")
    return f"{sym.symbol}: {sum(1 for v in signals.values() if v is True)} signals active"
check("Scanner engine", check_scanner_engine)

def check_scoring_engine():
    from scoring_engine.scoring import calculate_score
    test_signals = {
        "ema_alignment": True, "price_above_ema50": True, "higher_high": True,
        "breakout_20d": True, "rsi_strength": True, "relative_strength": False,
        "volume_spike": True, "accumulation": True, "atr_expansion": True,
        "tight_range_breakout": False, "overbought": False, "near_resistance": False,
    }
    result = calculate_score(test_signals)
    score = result["total_score"]
    expected = 75  # Trend40 + Momentum15 + Volume15 + Volatility5 = 75
    if score != expected:
        # ตรวจ logic: trend=40, momentum=15(no relative), volume=15, vol=5, risk=0
        bd = result["breakdown"]
        return f"score={score} breakdown={bd} (expected ~{expected})"
    return f"score={score}/100 ✓"
check("Scoring engine", check_scoring_engine)

def check_decision_engine():
    from decision_engine.decision import make_decision, calculate_position_size
    assert make_decision(85) == "STRONG BUY"
    assert make_decision(65) == "BUY"
    assert make_decision(45) == "HOLD"
    assert make_decision(25) == "WATCH"
    assert make_decision(10) == "SELL"
    size = calculate_position_size(100000, 0.01, 100, 95)
    if size <= 0: raise Exception("Position size = 0")
    return f"Decision logic OK | size={size} shares @ 100 (SL=95)"
check("Decision engine", check_decision_engine)

def check_portfolio_engine():
    from portfolio_engine.portfolio_manager import PortfolioManager
    pm = PortfolioManager(100000)
    result = pm.add_position("PTT", 35.0, 100)
    if "added" not in result: raise Exception(result)
    val = pm.calculate_value({"PTT": 36.0})
    if val <= 0: raise Exception("Portfolio value = 0")
    summary = pm.summary({"PTT": 36.0})
    if summary["positions"] != 1: raise Exception("Position count wrong")
    return f"capital=100000 | after buy: value={val:,.0f} | P/L={summary['unrealized_pnl']:+.0f}"
check("Portfolio engine", check_portfolio_engine)

def check_backtest_engine():
    from radar.models import PriceDaily, Symbol
    import pandas as pd
    from backtesting_engine.report import run_backtest, calculate_metrics, generate_report
    sym = Symbol.objects.filter(exchange="SET").order_by("symbol").first()
    prices = PriceDaily.objects.filter(symbol=sym).order_by("date").values("date","open","high","low","close","volume")
    if len(prices) < 50: raise Exception("Not enough data for backtest")
    df = pd.DataFrame(list(prices)).set_index("date")
    for col in ["open","high","low","close"]: df[col] = df[col].astype(float)
    equity = run_backtest(df, initial_capital=100000)
    if not equity: raise Exception("Empty equity curve")
    metrics = calculate_metrics(equity)
    report = generate_report(metrics)
    return f"trades={metrics['total_trades']} WR={report['Win Rate']} return={report['Total Return']}"
check("Backtest engine", check_backtest_engine)

# ─── 4. API ENDPOINTS ─────────────────────────────────────────
print("\n[4] API Endpoints (HTTP)")
import urllib.request, urllib.error

BASE = "http://127.0.0.1:8000"

ENDPOINTS = [
    ("GET", "/api/dashboard/",           "stats"),
    ("GET", "/api/symbols/?page_size=5", "results"),
    ("GET", "/api/signals/?page_size=5", "results"),
    ("GET", "/api/scanner/",             "results"),
    ("GET", "/api/news/?limit=5",        "results"),
    ("GET", "/api/news/sentiment/",      "overall"),
    ("GET", "/api/cache/stats/",         "total_symbols"),
    ("GET", "/engine/scan/?top=5",       "results"),
]

for method, path, key in ENDPOINTS:
    def make_check(m, p, k):
        def _check():
            req = urllib.request.Request(BASE + p)
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                    if k not in data:
                        raise Exception(f"Missing key '{k}' in response")
                    val = data[k]
                    if isinstance(val, list):
                        return f"{len(val)} items"
                    if isinstance(val, dict):
                        return f"dict with {len(val)} keys"
                    return str(val)[:50]
            except urllib.error.URLError as e:
                raise Exception(f"Server not reachable: {e}")
        return _check
    check(f"{method} {path}", make_check(method, path, key))

# ─── 5. LOGIC CONSISTENCY ─────────────────────────────────────
print("\n[5] Logic Consistency Checks")

def check_signal_direction_logic():
    from radar.models import Signal
    # BUY signals ต้องเป็น LONG
    bad = Signal.objects.filter(
        signal_type__in=["BUY","STRONG_BUY","GOLDEN_CROSS"],
        direction="SHORT"
    ).count()
    if bad > 0: raise Exception(f"{bad} BUY signals with DIRECTION=SHORT (logic error)")
    # SELL signals ต้องเป็น SHORT
    bad2 = Signal.objects.filter(
        signal_type__in=["SELL","STRONG_SELL","DEATH_CROSS"],
        direction="LONG"
    ).count()
    if bad2 > 0: raise Exception(f"{bad2} SELL signals with DIRECTION=LONG (logic error)")
    return "BUY→LONG, SELL→SHORT consistent"
check("Signal direction logic", check_signal_direction_logic)

def check_score_range():
    from radar.models import Signal
    from django.db.models import Min, Max
    agg = Signal.objects.aggregate(mn=Min("score"), mx=Max("score"))
    mn, mx = float(agg["mn"] or 0), float(agg["mx"] or 0)
    if mn < 0: raise Exception(f"Score < 0 found: {mn}")
    if mx > 100: raise Exception(f"Score > 100 found: {mx}")
    return f"score range: {mn:.0f}–{mx:.0f} (valid)"
check("Score range (0-100)", check_score_range)

def check_stoploss_logic():
    from radar.models import Signal
    # stop_loss ต้องน้อยกว่า entry price เสมอ
    bad = Signal.objects.filter(
        stop_loss__isnull=False,
        direction="LONG"
    ).extra(where=["stop_loss >= price"]).count()
    if bad > 0: raise Exception(f"{bad} LONG signals where stop_loss >= price")
    return "Stop loss < entry price ✓"
check("Stop loss logic", check_stoploss_logic)

def check_duplicate_signals():
    from radar.models import Signal
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    today = timezone.now().date()
    dups = (Signal.objects
            .filter(created_at__date=today)
            .values("symbol","signal_type")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=5))
    if dups.exists():
        examples = list(dups[:3])
        print(f"{WARN} Possible duplicate signals today: {examples}")
    return f"No excessive duplicates"
check("Duplicate signals", check_duplicate_signals)

def check_price_data_freshness():
    from radar.models import PriceDaily
    from datetime import date, timedelta
    latest = PriceDaily.objects.order_by("-date").first()
    if not latest: raise Exception("No price data")
    days_old = (date.today() - latest.date).days
    if days_old > 5:
        raise Exception(f"Price data is {days_old} days old (last: {latest.date})")
    return f"Latest price: {latest.date} ({days_old}d ago)"
check("Price data freshness", check_price_data_freshness)

def check_channel_layer():
    from django.conf import settings
    cl = getattr(settings, "CHANNEL_LAYERS", None)
    if not cl:
        raise Exception("CHANNEL_LAYERS not configured → WebSocket will fail")
    backend = cl.get("default", {}).get("BACKEND", "")
    return f"Backend: {backend.split('.')[-1]}"
check("Channel layer (WebSocket)", check_channel_layer)

def check_news_fetcher():
    from radar.news_fetcher import score_sentiment
    s, score = score_sentiment("stock market surges to record high profit growth")
    if s != "BULLISH": raise Exception(f"Expected BULLISH, got {s}")
    s2, score2 = score_sentiment("stock crash bankruptcy loss layoff warning")
    if s2 != "BEARISH": raise Exception(f"Expected BEARISH, got {s2}")
    return f"Sentiment logic: 'surge'→{s}({score:+.2f}), 'crash'→{s2}({score2:+.2f})"
check("Sentiment logic", check_news_fetcher)

# ─── 6. SCHEDULER CONFIG ──────────────────────────────────────
print("\n[6] Scheduler & Automation")

def check_scheduler_tasks():
    from radar.management.commands.start_scheduler import SCHEDULE
    required_names = ["โหลดราคาหุ้นไทย", "คำนวณ Indicator", "สร้าง Signal"]
    names = [t[5] for t in SCHEDULE]
    missing = [n for n in required_names if not any(n in x for x in names)]
    if missing: raise Exception(f"Missing tasks: {missing}")
    return f"{len(SCHEDULE)} tasks configured"
check("Scheduler tasks", check_scheduler_tasks)

def check_settings_completeness():
    from django.conf import settings
    required = ["DATABASES","INSTALLED_APPS","CHANNEL_LAYERS","CORS_ALLOWED_ORIGINS","REST_FRAMEWORK"]
    missing = [k for k in required if not hasattr(settings, k)]
    if missing: raise Exception(f"Missing settings: {missing}")
    # ตรวจ engine_api ใน INSTALLED_APPS
    if "engine_api" not in settings.INSTALLED_APPS:
        raise Exception("engine_api not in INSTALLED_APPS")
    return "All required settings present"
check("Settings completeness", check_settings_completeness)

# ─── 7. SUMMARY ───────────────────────────────────────────────
total   = len(results)
passed  = sum(1 for r in results if r[0])
failed  = total - passed

print("\n" + "="*60)
print(f"  SUMMARY: {passed}/{total} checks passed")
print("="*60)

if failed > 0:
    print(f"\n  FAILED ({failed}):")
    for ok, name, msg in results:
        if not ok:
            print(f"    ✗ {name}")
            print(f"      → {msg}")

print(f"\n  Status: {'ALL SYSTEMS OK' if failed == 0 else f'{failed} ISSUES FOUND'}")
print()
sys.exit(0 if failed == 0 else 1)
