import django, os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'stockradar.settings'
sys.path.insert(0, 'D:/stockradar')
django.setup()

from radar.models import Profile
print("Profile fields:", [f.name for f in Profile._meta.get_fields()])
print()

from django.contrib.auth.models import User
u = User.objects.filter(is_superuser=True).first()
p = u.profile
print(f"User: {u.username} | is_superuser: {u.is_superuser}")
print(f"Profile plan: {getattr(p, 'plan', 'N/A')}")
print(f"Profile tier: {getattr(p, 'tier', 'N/A')}")
print(f"Profile subscription: {getattr(p, 'subscription', 'N/A')}")
