import requests, json

print("=== ENGINE SCAN TEST ===")
try:
    r = requests.get("http://127.0.0.1:8000/engine/scan/?top=5&min_score=0", timeout=10)
    print(f"Status: {r.status_code}")
    d = r.json()
    print(f"Count: {d.get('count')}")
    if d.get('results'):
        print(f"First result: {json.dumps(d['results'][0], indent=2)}")
    else:
        print("No results - checking signals in DB...")
        import django, os, sys
        os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
        sys.path.insert(0, 'D:/stockradar')
        django.setup()
        from radar.models import Signal
        total = Signal.objects.count()
        long_signals = Signal.objects.filter(direction="LONG").count()
        print(f"  Total signals: {total}")
        print(f"  LONG signals: {long_signals}")
        from django.utils import timezone
        from datetime import timedelta
        week = timezone.now() - timedelta(days=7)
        recent = Signal.objects.filter(created_at__gte=week).count()
        print(f"  Recent 7d signals: {recent}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== ENGINE ANALYZE TEST ===")
try:
    r = requests.get("http://127.0.0.1:8000/engine/analyze/PTT/", timeout=15)
    print(f"Status: {r.status_code}")
    d = r.json()
    if d.get('error'):
        print(f"Error: {d['error']}")
    else:
        print(f"Symbol: {d.get('symbol')}")
        print(f"Decision: {d.get('decision')}")
        print(f"Score: {d.get('score')}")
        print(f"Reasons: {d.get('reasons')}")
except Exception as e:
    print(f"ERROR: {e}")
