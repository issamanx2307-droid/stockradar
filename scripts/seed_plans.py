import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from radar.models import SubscriptionPlan, Profile
from django.contrib.auth.models import User

# สร้าง plans
plans = [
    dict(name="Free",    tier="FREE",    price_thb=0,   duration_days=36500,
         description="ทดลองใช้ฟรี ไม่จำกัดเวลา",
         features=["Watchlist 3 ตัว","Scanner 20 ผลลัพธ์","กราฟพื้นฐาน","ปฏิทินเศรษฐกิจ"]),
    dict(name="Pro",     tier="PRO",     price_thb=299, duration_days=30,
         description="สมาชิก Pro เต็มรูปแบบ",
         features=["Watchlist 10 ตัว","Scanner ไม่จำกัด","Fundamental Data","Backtest 3 ปี",
                   "P/L History Chart","ปฏิทินเศรษฐกิจ","Top Opportunities"]),
    dict(name="Premium", tier="PREMIUM", price_thb=599, duration_days=30,
         description="สมาชิก Premium ไม่จำกัดทุกฟีเจอร์",
         features=["ทุกอย่างใน Pro","Watchlist 20 ตัว","Backtest 5 ปี",
                   "Scanner 500 ผลลัพธ์","Priority Support"]),
]

for p in plans:
    obj, created = SubscriptionPlan.objects.get_or_create(
        name=p["name"], defaults=p
    )
    if created:
        print(f"Created: {obj}")
    else:
        print(f"Exists:  {obj}")

# Superuser → PREMIUM tier
for u in User.objects.filter(is_superuser=True):
    try:
        profile = u.profile
        if profile.tier != "PREMIUM":
            profile.tier = "PREMIUM"
            profile.save(update_fields=["tier"])
            print(f"Updated {u.username} → PREMIUM")
        else:
            print(f"{u.username} already PREMIUM")
    except Exception as e:
        print(f"Error: {e}")

print("\nDone!")
