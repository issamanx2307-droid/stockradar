#!/usr/bin/env bash
# build.sh — Render.com build script
set -e

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Creating superuser (first deploy only) ==="
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
import os
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        username=os.environ.get("ADMIN_USER", "admin"),
        email=os.environ.get("ADMIN_EMAIL", "admin@stockradar.com"),
        password=os.environ.get("ADMIN_PASSWORD", "changeme123"),
    )
    print("Superuser created")
else:
    print("Superuser already exists")
EOF

echo "=== Build complete ==="
