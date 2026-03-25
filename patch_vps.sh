#!/bin/bash
# ============================================================
# patch_vps.sh — แก้ปัญหา Mixed Content + CSRF บน VPS
# รันบน VPS: bash /opt/stockradar/patch_vps.sh
# ============================================================
set -e

echo "🔧 เริ่ม patch VPS..."

# ── 1. Pull โค้ดใหม่จาก GitHub ───────────────────────────
cd /opt/stockradar
git pull
echo "✅ git pull สำเร็จ"

# ── 2. Rebuild frontend ด้วย HTTPS URL ───────────────────
cd /opt/stockradar/frontend

cat > .env.production << 'FRONTEOF'
VITE_API_URL=https://radarhoon.com/api
VITE_GOOGLE_CLIENT_ID=604864460946-q4bcklavlc972jsc6ifsj59ll9760usp.apps.googleusercontent.com
FRONTEOF

npm ci && npm run build
echo "✅ Frontend build สำเร็จ (HTTPS)"

# ── 3. Restart Django ─────────────────────────────────────
cd /opt/stockradar
source .venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
deactivate

systemctl restart stockradar
echo "✅ Django restarted"

# ── 4. Restart Celery ─────────────────────────────────────
systemctl restart stockradar-celery 2>/dev/null && echo "✅ Celery Worker restarted" || echo "⚠️  Celery Worker ยังไม่ได้ติดตั้ง (รัน setup_services.sh)"
systemctl restart stockradar-celerybeat 2>/dev/null && echo "✅ Celery Beat restarted" || echo "⚠️  Celery Beat ยังไม่ได้ติดตั้ง"

# ── 5. Reload Nginx ───────────────────────────────────────
nginx -t && systemctl reload nginx
echo "✅ Nginx reloaded"

# ── 5. ตรวจสอบผล ──────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ทดสอบ API..."
curl -sI https://radarhoon.com/api/dashboard/ | head -5
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Patch เสร็จสมบูรณ์!"
echo "🌐 เข้าได้ที่: https://radarhoon.com"
