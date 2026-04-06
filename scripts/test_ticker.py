import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from radar.ticker_api import fetch_ticker_data
data = fetch_ticker_data()
print(f"Got {len(data)} items:")
for d in data:
    arrow = "▲" if d["up"] else "▼"
    print(f"  {d['label']:12} {d['price']:>12.4f}  {arrow} {d['change_pct']:+.2f}%")
