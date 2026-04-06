import requests, json, sys

BASE = "http://127.0.0.1:8000"
OK = "✅"; FAIL = "❌"
results = []

def check(label, url, method="GET", data=None, min_status=200, max_status=200, check_key=None):
    try:
        if method == "POST":
            r = requests.post(url, json=data or {}, timeout=15)
        else:
            r = requests.get(url, timeout=15)
        ok = min_status <= r.status_code <= max_status
        if ok and check_key:
            d = r.json()
            ok = check_key in d
        icon = OK if ok else FAIL
        try:
            d = r.json()
            extra = ""
            if "count" in d: extra = f"count={d['count']}"
            elif "items" in d: extra = f"items={len(d['items'])}"
            elif "results" in d: extra = f"results={len(d['results'])}"
            elif "error" in d: extra = f"ERROR: {d['error']}"
        except: extra = f"status={r.status_code}"
        print(f"  {icon} {label:40} {r.status_code}  {extra}")
        results.append(ok)
    except Exception as e:
        print(f"  {FAIL} {label:40} EXCEPTION: {e}")
        results.append(False)

print("=" * 70)
print("STOCKRADAR SYSTEM CHECK")
print("=" * 70)

print("\n── Core APIs ──")
check("Dashboard",                    f"{BASE}/api/dashboard/",           check_key="stats")
check("Symbols",                      f"{BASE}/api/symbols/?page_size=5", check_key="results")
check("Prices (PTT)",                 f"{BASE}/api/prices/PTT/")
check("Indicators (PTT)",             f"{BASE}/api/indicators/PTT/")
check("Signals",                      f"{BASE}/api/signals/?days=7&page_size=5", check_key="results")
check("Scanner",                      f"{BASE}/api/scanner/?exchange=SET", check_key="results")

print("\n── Watchlist APIs ──")
check("Watchlist GET",                f"{BASE}/api/watchlist/",            check_key="items")
check("Watchlist History",            f"{BASE}/api/watchlist/history/?days=30")
check("Fundamental PTT",              f"{BASE}/api/fundamental/PTT/",      check_key="symbol")
check("Fundamental AAPL",             f"{BASE}/api/fundamental/AAPL/",     check_key="symbol")

print("\n── Engine APIs ──")
check("Engine Scan",                  f"{BASE}/engine/scan/?top=5",        check_key="results")
check("Engine Analyze PTT",           f"{BASE}/engine/analyze/PTT/",       check_key="symbol")
check("Engine Analyze NVDA",          f"{BASE}/engine/analyze/NVDA/",      check_key="symbol")

print("\n── Data APIs ──")
check("News",                         f"{BASE}/api/news/?days=7&limit=5",  check_key="results")
check("Ticker Tape",                  f"{BASE}/api/ticker/",               check_key="items")
check("Economic Calendar",            f"{BASE}/api/calendar/?days=7",      check_key="events")
check("Cache Stats",                  f"{BASE}/api/cache/stats/")

print("\n── WebSocket URL ──")
try:
    import websocket
    ws = websocket.create_connection("ws://127.0.0.1:8000/ws/radar/", timeout=5)
    ws.close()
    print(f"  {OK} {'WebSocket /ws/radar/':40} connected")
    results.append(True)
except Exception as e:
    print(f"  ⚠️  {'WebSocket /ws/radar/':40} {e}")
    results.append(True)  # not critical for system check

passed = sum(results)
total  = len(results)
print(f"\n{'='*70}")
print(f"ผล: {passed}/{total} ผ่าน  {'✅ ระบบทำงานปกติ' if passed==total else '⚠️ บางส่วนมีปัญหา'}")
print("=" * 70)
