import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from radar.models import Signal
from django.utils import timezone
from datetime import timedelta

print("=== Signal DB Stats ===")
print(f"Total signals: {Signal.objects.count()}")
for d in [1, 7, 30, 90, 365]:
    since = timezone.now() - timedelta(days=d)
    n = Signal.objects.filter(created_at__gte=since, direction="LONG").count()
    print(f"  LONG signals last {d}d: {n}")

# ตรวจ score distribution
from django.db.models import Min, Max, Avg
stats = Signal.objects.filter(direction="LONG").aggregate(
    min_score=Min("score"), max_score=Max("score"), avg_score=Avg("score"))
print(f"\nScore stats (LONG): {stats}")

# ตรวจ latest signal date
latest = Signal.objects.order_by("-created_at").first()
if latest:
    print(f"Latest signal: {latest.created_at} ({latest.symbol.symbol})")
