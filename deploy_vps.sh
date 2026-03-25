#!/bin/bash
# ============================================================
# StockRadar VPS Deploy Script — Hostinger Ubuntu 22.04
# รันครั้งเดียว ติดตั้งทุกอย่างอัตโนมัติ
# ============================================================
set -e

echo "🚀 StockRadar VPS Setup เริ่มต้น..."

# ── 1. Update system ──────────────────────────────────────
apt update && apt upgrade -y
apt install -y git python3 python3-pip python3-venv nginx curl \
    build-essential libpq-dev postgresql postgresql-contrib \
    certbot python3-certbot-nginx ufw

# ── 2. Firewall ───────────────────────────────────────────
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

# ── 3. Clone repo ─────────────────────────────────────────
cd /opt
if [ -d "stockradar" ]; then
    cd stockradar && git pull
else
    git clone https://github.com/issamanx2307-droid/stockradar.git
    cd stockradar
fi

# ── 4. Python venv ────────────────────────────────────────
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn

# ── 5. .env file ──────────────────────────────────────────
if [ ! -f .env ]; then
cat > .env << 'ENVEOF'
DJANGO_SECRET_KEY=CHANGE_THIS_TO_RANDOM_SECRET_KEY
DEBUG=False
ALLOWED_HOSTS=187.127.107.228,srv1522191.hstgr.cloud,radarhoon.com,www.radarhoon.com
DATABASE_URL=sqlite:////opt/stockradar/db.sqlite3
REDIS_URL=
CORS_ORIGINS=https://radarhoon.com,http://www.radarhoon.com,http://187.127.107.228
GOOGLE_CLIENT_ID=604864460946-q4bcklavlc972jsc6ifsj59ll9760usp.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=
ENVEOF
echo "⚠️  กรุณาแก้ไข .env ก่อน continue!"
fi

# ── 6. Django setup ───────────────────────────────────────
export $(cat .env | grep -v '#' | xargs)
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# ── 7. Daphne systemd service ─────────────────────────────
cat > /etc/systemd/system/stockradar.service << 'SVCEOF'
[Unit]
Description=StockRadar Django ASGI (Daphne)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/stockradar
EnvironmentFile=/opt/stockradar/.env
ExecStart=/opt/stockradar/.venv/bin/daphne \
    -b 127.0.0.1 -p 8000 \
    stockradar.asgi:application
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable stockradar
systemctl restart stockradar

# ── 8. Build React frontend ───────────────────────────────
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs
cd /opt/stockradar/frontend

cat > .env.production << 'FRONTEOF'
VITE_API_URL=https://radarhoon.com/api
VITE_GOOGLE_CLIENT_ID=604864460946-q4bcklavlc972jsc6ifsj59ll9760usp.apps.googleusercontent.com
FRONTEOF

npm ci && npm run build

# ── 9. Nginx config ───────────────────────────────────────
cat > /etc/nginx/sites-available/stockradar << 'NGINXEOF'
server {
    listen 80;
    server_name 187.127.107.228 srv1522191.hstgr.cloud radarhoon.com www.radarhoon.com;

    # React frontend
    root /opt/stockradar/frontend/dist;
    index index.html;

    # API → Django
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Engine API → Django
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

    # Admin + Static
    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }
    location /static/ {
        alias /opt/stockradar/staticfiles/;
        expires 30d;
    }
    location /accounts/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
    }

    # React SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/stockradar /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "✅ ติดตั้งเสร็จสมบูรณ์!"
echo "🌐 เข้าได้ที่: http://187.127.107.228"
echo "⚠️  อย่าลืมแก้ไข /opt/stockradar/.env (SECRET_KEY)"
