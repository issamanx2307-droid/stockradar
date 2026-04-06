import django, os, sys, json, traceback

os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from django.contrib.auth.models import User
from radar.models import Watchlist, WatchlistItem, WatchlistTrade, Symbol, PriceDaily

u = User.objects.filter(is_superuser=True).first()
print(f"User: {u}")

# ── ทดสอบ watchlist logic โดยตรง ──
print("\n=== WATCHLIST LOGIC TEST ===")
try:
    from radar.views import _get_or_create_watchlist, _calc_position, _analyze_watchlist_item
    wl = _get_or_create_watchlist(u)
    print(f"Watchlist: {wl}")
    items = wl.items.select_related("symbol").prefetch_related("trades").all()
    print(f"Items: {items.count()}")
    for item in items:
        print(f"  Item: {item.symbol.symbol}")
        pos = _calc_position(item)
        print(f"  Position: {pos}")
        analysis = _analyze_watchlist_item(item)
        print(f"  Analysis keys: {list(analysis.keys())}")
        if analysis.get('error'):
            print(f"  ERROR: {analysis['error']}")
        else:
            print(f"  current_price: {analysis.get('current_price')}")
            print(f"  action: {analysis.get('action')}")
except Exception as e:
    print(f"WATCHLIST ERROR: {e}")
    traceback.print_exc()

# ── ทดสอบ fundamental engine ──
print("\n=== FUNDAMENTAL ENGINE TEST ===")
try:
    from radar.fundamental_engine import get_fundamental, _ticker_symbol
    
    # ทดสอบ ticker conversion
    t = _ticker_symbol("PTT", "SET")
    print(f"Ticker: PTT → {t}")
    
    # ทดสอบ fetch (ไม่ใช้ cache)
    from django.core.cache import cache
    cache.delete("fundamental:PTT")
    
    print("Fetching PTT fundamental...")
    result = get_fundamental("PTT", exchange="SET")
    if result.get('error'):
        print(f"ERROR: {result['error']}")
    else:
        print(f"  name: {result.get('name')}")
        print(f"  pe_trailing: {result.get('pe_trailing')}")
        print(f"  eps: {result.get('eps')}")
        print(f"  revenue_fmt: {result.get('revenue_fmt')}")
        print(f"  quarterly Q count: {len(result.get('quarterly_financials', []))}")
        print("  FUNDAMENTAL OK")
except Exception as e:
    print(f"FUNDAMENTAL ERROR: {e}")
    traceback.print_exc()
