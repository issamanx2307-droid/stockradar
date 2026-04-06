#!/bin/bash
# ============================================================
# setup_services.sh — ติดตั้ง systemd services ให้ครบ
# รันบน VPS ครั้งเดียว: bash /opt/stockradar/setup_services.sh
#
# Services ที่จะติดตั้ง:
#   1. stockradar      — Daphne ASGI (Django)
#   2. stockradar-celery      — Celery Worker
#   3. stockradar-celerybeat  — Celery Beat (scheduler)
#   4. redis-server    — Redis (broker + cache)
# ============================================================
set -e

APP_DIR="/opt/stockradar"
VENV="$APP_DIR/.venv"
ENV_FILE="$APP_DIR/.env"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  StockRadar — ติดตั้ง Keep-Alive Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── ตรวจสอบ root ──────────────────────────────────────────
if [ "$EUID" -ne 0 ]; then
  echo "❌ กรุณารันด้วย sudo หรือ root"
  exit 1
fi

cd "$APP_DIR"

# ═══════════════════════════════════════════════════════════
# 1. ติดตั้ง Redis
# ═══════════════════════════════════════════════════════════
echo ""
echo "📦 [1/5] ติดตั้ง Redis..."
apt-get install -y redis-server > /dev/null

# ตั้งค่า Redis ให้ bind localhost เท่านั้น
sed -i 's/^bind .*/bind 127.0.0.1 -::1/' /etc/redis/redis.conf
sed -i 's/^# maxmemory-policy.*/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

systemctl enable redis-server
systemctl restart redis-server
echo "✅ Redis รันที่ redis://127.0.0.1:6379/0"

# ═══════════════════════════════════════════════════════════
# 2. สร้างโฟลเดอร์พื้นฐาน
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔧 [2/5] สร้างโฟลเดอร์พื้นฐาน..."

mkdir -p "$APP_DIR/logs"
mkdir -p "$APP_DIR/run"

# ═══════════════════════════════════════════════════════════
# 3. อัปเดต .env — เพิ่ม REDIS_URL
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔧 [3/5] อัปเดต .env..."

if grep -q "^REDIS_URL=" "$ENV_FILE"; then
  # แก้บรรทัดที่มีอยู่
  sed -i 's|^REDIS_URL=.*|REDIS_URL=redis://127.0.0.1:6379/0|' "$ENV_FILE"
else
  echo "REDIS_URL=redis://127.0.0.1:6379/0" >> "$ENV_FILE"
fi
echo "✅ REDIS_URL=redis://127.0.0.1:6379/0"

# ═══════════════════════════════════════════════════════════
# 4. สร้าง stockradar.service (Daphne) — อัปเดต
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔧 [4/5] สร้าง stockradar.service (Daphne)..."

cat > /etc/systemd/system/stockradar.service << 'EOF'
[Unit]
Description=StockRadar — Django ASGI (Daphne)
After=network.target redis-server.service
Wants=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stockradar
EnvironmentFile=/opt/stockradar/.env
ExecStartPre=/bin/mkdir -p /opt/stockradar/logs
ExecStart=/opt/stockradar/.venv/bin/daphne \
    -b 127.0.0.1 -p 8000 \
    stockradar.asgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stockradar

[Install]
WantedBy=multi-user.target
EOF

echo "✅ stockradar.service"

# ═══════════════════════════════════════════════════════════
# 4. สร้าง stockradar-celery.service (Celery Worker)
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔧 [4/5] สร้าง stockradar-celery.service (Worker)..."

cat > /etc/systemd/system/stockradar-celery.service << 'EOF'
[Unit]
Description=StockRadar — Celery Worker
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stockradar
EnvironmentFile=/opt/stockradar/.env
ExecStart=/opt/stockradar/.venv/bin/celery \
    -A stockradar worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=100 \
    -n worker@%h
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stockradar-celery

[Install]
WantedBy=multi-user.target
EOF

echo "✅ stockradar-celery.service"

# ═══════════════════════════════════════════════════════════
# 5. สร้าง stockradar-celerybeat.service (Celery Beat)
# ═══════════════════════════════════════════════════════════
echo ""
echo "🔧 [5/5] สร้าง stockradar-celerybeat.service (Beat)..."

# สร้าง folder สำหรับ beat schedule file
mkdir -p /opt/stockradar/run

cat > /etc/systemd/system/stockradar-celerybeat.service << 'EOF'
[Unit]
Description=StockRadar — Celery Beat Scheduler
After=network.target redis-server.service stockradar-celery.service
Requires=redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stockradar
EnvironmentFile=/opt/stockradar/.env
ExecStart=/opt/stockradar/.venv/bin/celery \
    -A stockradar beat \
    --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --pidfile=/opt/stockradar/run/celerybeat.pid
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=stockradar-celerybeat

[Install]
WantedBy=multi-user.target
EOF

echo "✅ stockradar-celerybeat.service"

# ═══════════════════════════════════════════════════════════
# ติดตั้ง django-celery-beat (ถ้ายังไม่มี)
# ═══════════════════════════════════════════════════════════
echo ""
echo "📦 ตรวจสอบ django-celery-beat..."
source "$VENV/bin/activate"

if ! python -c "import django_celery_beat" 2>/dev/null; then
  pip install django-celery-beat --quiet
  echo "✅ ติดตั้ง django-celery-beat"
else
  echo "✅ django-celery-beat มีอยู่แล้ว"
fi

# Migrate django_celery_beat tables
python manage.py migrate django_celery_beat --noinput 2>/dev/null || true
deactivate

# ═══════════════════════════════════════════════════════════
# Enable + Start ทุก services
# ═══════════════════════════════════════════════════════════
echo ""
echo "🚀 เปิดใช้งานและรัน services..."

systemctl daemon-reload

for svc in redis-server stockradar stockradar-celery stockradar-celerybeat; do
  systemctl enable "$svc"
  systemctl restart "$svc"
  sleep 2
  status=$(systemctl is-active "$svc")
  if [ "$status" = "active" ]; then
    echo "  ✅ $svc — $status"
  else
    echo "  ⚠️  $svc — $status (ดู log: journalctl -u $svc -n 20)"
  fi
done

# ═══════════════════════════════════════════════════════════
# สรุปสถานะ
# ═══════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  สถานะ Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
systemctl status redis-server stockradar stockradar-celery stockradar-celerybeat \
  --no-pager -l --lines=3 2>/dev/null || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ ติดตั้งเสร็จสมบูรณ์!"
echo ""
echo "  คำสั่งที่ใช้บ่อย:"
echo "  • ดูสถานะทั้งหมด  : bash /opt/stockradar/status.sh"
echo "  • ดู log Django   : journalctl -u stockradar -f"
echo "  • ดู log Celery   : journalctl -u stockradar-celery -f"
echo "  • ดู log Beat     : journalctl -u stockradar-celerybeat -f"
echo "  • Restart ทั้งหมด : bash /opt/stockradar/restart_all.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
