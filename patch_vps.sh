#!/bin/bash
# ============================================================
# patch_vps.sh — แก้ไข radarhoon.com ให้ทำงานได้
# รันบน VPS ด้วย: bash /opt/stockradar/patch_vps.sh
# ============================================================
set -e

echo "🔧 Patching StockRadar for radarhoon.com..."

# ── 1. Generate SECRET_KEY ────────────────────────────────
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
echo "✅ Generated new SECRET_KEY"

# ── 2. แก้ไข .env ─────────────────────────────────────────
cat > /opt/stockradar/.env << ENVEOF
DJANGO_SECRET_KEY=${NEW_SECRET}
DEBUG=False
ALLOWED_HOSTS=187.127.107.228,srv1522191.hstgr.cloud,radarhoon.com,www.radarhoon.com
DATABASE_URL=sqlite:////opt/stockradar/db.sqlite3
REDIS_URL=
CORS_ORIGINS=https://radarhoon.com,http://www.radarhoon.com,http://187.127.107.228
GOOGLE_CLIENT_ID=604864460946-q4bcklavlc972jsc6ifsj59ll9760usp.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=
ENVEOF
echo "✅ .env updated"

# ── 3. แก้ไข Nginx server_name ─────────────────────────────
sed -i 's/server_name 187.127.107.228 srv1522191.hstgr.cloud;/server_name 187.127.107.228 srv1522191.hstgr.cloud radarhoon.com www.radarhoon.com;/' \
    /etc/nginx/sites-available/stockradar
echo "✅ Nginx server_name updated"

# ── 4. Test & restart ──────────────────────────────────────
nginx -t
systemctl restart nginx
systemctl restart stockradar
echo "✅ Nginx + Stockradar restarted"

# ── 5. ตรวจสอบสถานะ ────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 สถานะ Stockradar service:"
systemctl status stockradar --no-pager -l | tail -10
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 สถานะ Nginx:"
systemctl status nginx --no-pager | tail -5
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 ทดสอบ: curl -I http://radarhoon.com"
curl -sI http://radarhoon.com | head -5 || echo "⚠️  DNS ยังไม่ propagate หรือ domain ยังไม่ชี้มา VPS"
echo ""
echo "✅ Patch เสร็จสมบูรณ์!"
