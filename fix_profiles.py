
from django.contrib.auth.models import User
from radar.models import Profile

count = 0
for user in User.objects.all():
    if not hasattr(user, 'profile'):
        Profile.objects.get_or_create(user=user)
        count += 1
print(f"Checked {User.objects.count()} users. Created {count} missing profiles.")
