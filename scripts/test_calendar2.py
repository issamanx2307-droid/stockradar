import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from radar.economic_calendar import fetch_economic_calendar
data = fetch_economic_calendar(days_ahead=7)
print(f"Events: {len(data)}")
for ev in data[:8]:
    print(f"  {ev['flag']} {ev['country']} | {ev['date']} {ev['time']} | [{ev['impact']:6}] {ev['event'][:60]}")
