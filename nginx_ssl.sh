#!/bin/bash
# ============================================================
# nginx_ssl.sh — ตั้ง Nginx + SSL สำหรับ radarhoon.com
# รันบน VPS: bash /opt/stockradar/nginx_ssl.sh
# ============================================================
set -e

echo "🔧 กำลังตั้งค่า Nginx SSL..."

cat > /etc/nginx/sites-available/stockradar << 'NGINXEOF'
# HTTP → redirect to HTTPS
server {
    listen 80;
    server_name radarhoon.com www.radarhoon.com 187.127.107.228 srv1522191.hstgr.cloud;
    return 301 https://radarhoon.com$request_uri;
}

# HTTPS main
server {
    listen 443 ssl;
    server_name radarhoon.com www.radarhoon.com;

    ssl_certificate     /etc/letsencrypt/live/radarhoon.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/radarhoon.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # React frontend
    root /opt/stockradar/frontend/dist;
    index index.html;

    # Django API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Engine API
    location /engine/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Django Admin
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Django accounts (allauth)
    location /accounts/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /opt/stockradar/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # React SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF

echo "✅ Nginx config เขียนแล้ว"

# Test config
nginx -t
echo "✅ Nginx config syntax OK"

# Reload
systemctl reload nginx
echo "✅ Nginx reloaded"

# อัพเดต .env ให้รองรับ HTTPS
sed -i 's|CORS_ORIGINS=.*|CORS_ORIGINS=https://radarhoon.com,https://www.radarhoon.com|' /opt/stockradar/.env
echo "✅ .env CORS_ORIGINS อัพเดตเป็น HTTPS"

# Restart app
systemctl restart stockradar
echo "✅ Stockradar restarted"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 ทดสอบ:"
curl -sI https://radarhoon.com | head -5 || echo "⚠️  ยังเข้าไม่ได้ ดู log ด้วย: journalctl -u stockradar -n 20"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ ตั้งค่า SSL เสร็จสมบูรณ์!"
echo "🔒 เข้าได้ที่: https://radarhoon.com"
