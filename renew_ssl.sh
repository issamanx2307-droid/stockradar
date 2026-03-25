#!/bin/bash
# ============================================================
# renew_ssl.sh — Auto-renew SSL สำหรับ radarhoon.com
# รันอัตโนมัติผ่าน cron ทุกเดือน
# ============================================================

LOG=/var/log/letsencrypt/renew_ssl.log
EMAIL="issamanx@gmail.com"

echo "========================================" >> $LOG
echo "$(date) — เริ่ม SSL renewal check" >> $LOG

# หยุด Nginx ชั่วคราว เพื่อให้ certbot ใช้ port 80
systemctl stop nginx

# ลอง renew (standalone mode — ไม่ต้องการ Nginx)
certbot renew --standalone --quiet 2>> $LOG
RESULT=$?

# เปิด Nginx กลับมา
systemctl start nginx

if [ $RESULT -eq 0 ]; then
    echo "$(date) — ✅ Renewal สำเร็จ หรือยังไม่ถึงเวลา renew" >> $LOG
    # reload nginx ให้ใช้ cert ใหม่
    systemctl reload nginx
else
    echo "$(date) — ❌ Renewal ล้มเหลว กรุณาตรวจสอบ" >> $LOG
    # ส่ง email แจ้งเตือน (ถ้ามี mail server)
    echo "SSL renewal failed for radarhoon.com on $(date)" | \
        mail -s "⚠️ SSL Renewal Failed - radarhoon.com" $EMAIL 2>/dev/null || true
fi

echo "$(date) — จบ SSL renewal check" >> $LOG
