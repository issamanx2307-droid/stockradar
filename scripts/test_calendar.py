import requests, json
r = requests.get("http://127.0.0.1:8000/api/calendar/?days=7", timeout=15)
d = r.json()
print(f"Status: {r.status_code} | Count: {d.get('count')}")
for ev in d.get("events", [])[:5]:
    print(f"  {ev['flag']} {ev['country']} | {ev['date']} {ev['time']} | [{ev['impact']:6}] {ev['event']}")
