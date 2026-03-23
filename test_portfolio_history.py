import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from django.contrib.auth.models import User
u = User.objects.filter(is_superuser=True).first()
print(f"User: {u}")

from radar.portfolio_history import calc_portfolio_history
data = calc_portfolio_history(u, days=90)
print(f"History points: {len(data)}")
if data:
    print(f"First: {data[0]}")
    print(f"Last:  {data[-1]}")
    # check fields
    if data[0]:
        print(f"Keys: {list(data[0].keys())}")
