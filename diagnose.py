import django, os, sys, requests, json

os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from django.contrib.auth.models import User
from radar.models import Watchlist, WatchlistItem, WatchlistTrade, Symbol, PriceDaily

print("=== WATCHLIST DIAGNOSIS ===")
u = User.objects.filter(is_superuser=True).first()
print(f"superuser: {u}")

wl_count = Watchlist.objects.count()
item_count = WatchlistItem.objects.count()
trade_count = WatchlistTrade.objects.count()
print(f"Watchlist records: {wl_count}")
print(f"WatchlistItem records: {item_count}")
print(f"WatchlistTrade records: {trade_count}")

if u:
    wl, created = Watchlist.objects.get_or_create(user=u)
    print(f"User watchlist: {wl} (created={created})")
    print(f"Items in watchlist: {wl.items.count()}")

print("\n=== WATCHLIST API TEST ===")
try:
    r = requests.get("http://127.0.0.1:8000/api/watchlist/", timeout=5)
    print(f"GET /api/watchlist/ → {r.status_code}")
    d = r.json()
    print(f"Response keys: {list(d.keys())}")
    print(f"Items count: {d.get('count', 'N/A')}")
    if d.get('items'):
        print(f"First item: {d['items'][0].get('symbol', 'N/A')}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== FUNDAMENTAL API TEST ===")
try:
    r = requests.get("http://127.0.0.1:8000/api/fundamental/PTT/", timeout=15)
    print(f"GET /api/fundamental/PTT/ → {r.status_code}")
    d = r.json()
    if d.get('error'):
        print(f"ERROR: {d['error']}")
    else:
        print(f"Symbol: {d.get('symbol')}")
        print(f"Name: {d.get('name')}")
        print(f"PE: {d.get('pe_trailing')}")
        print(f"EPS: {d.get('eps')}")
        print(f"Fetched at: {d.get('fetched_at')}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== URL CHECK ===")
from django.urls import reverse
try:
    print("watchlist-list:", reverse('watchlist-list'))
    print("fundamental:", reverse('fundamental', args=['PTT']))
except Exception as e:
    print(f"URL ERROR: {e}")
