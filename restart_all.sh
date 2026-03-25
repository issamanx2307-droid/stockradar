#!/bin/bash
# restart_all.sh — Restart ทุก services พร้อมกัน
# รัน: bash /opt/stockradar/restart_all.sh

echo "🔄 กำลัง restart services..."

systemctl restart redis-server
echo "  ✅ Redis"

systemctl restart stockradar
echo "  ✅ Django (Daphne)"

systemctl restart stockradar-celery
echo "  ✅ Celery Worker"

systemctl restart stockradar-celerybeat
echo "  ✅ Celery Beat"

nginx -t && systemctl reload nginx
echo "  ✅ Nginx"

echo ""
echo "✅ Restart เสร็จสิ้น"
echo "📊 ดูสถานะ: bash /opt/stockradar/status.sh"
