import requests
r = requests.get("http://127.0.0.1:8000/api/ticker/", timeout=10)
d = r.json()
print(f"Status: {r.status_code} | Items: {len(d.get('items', []))}")
for item in d.get("items", [])[:5]:
    arrow = "▲" if item["up"] else "▼"
    print(f"  {item['label']:12} {item['price']:>12.2f}  {arrow} {item['change_pct']:+.2f}%")
