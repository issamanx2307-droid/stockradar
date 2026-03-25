#!/bin/bash
# ============================================================
# setup_cron.sh — ตั้ง cron job สำหรับ auto-renew SSL
# รันบน VPS: bash /opt/stockradar/setup_cron.sh
# ============================================================
set -e

echo "🔧 ตั้งค่า SSL Auto-Renew..."

# คัดลอก renew script ไปที่เหมาะสม
cat > /opt/stockradar/renew_ssl.sh << 'RENEWEOF'
#!/bin/bash
LOG=/var/log/letsencrypt/renew_ssl.log
echo "========================================" >> $LOG
echo "$(date) — เริ่ม SSL renewal check" >> $LOG
systemctl stop nginx
certbot renew --standalone --quiet 2>> $LOG
RESULT=$?
systemctl start nginx
if [ $RESULT -eq 0 ]; then
    echo "$(date) — ✅ Renewal สำเร็จ หรือยังไม่ถึงเวลา renew" >> $LOG
    systemctl reload nginx
else
    echo "$(date) — ❌ Renewal ล้มเหลว" >> $LOG
fi
echo "$(date) — จบ SSL renewal check" >> $LOG
RENEWEOF

chmod +x /opt/stockradar/renew_ssl.sh
echo "✅ renew_ssl.sh พร้อมแล้ว"

# ลบ cron เดิม (ถ้ามี) แล้วเพิ่มใหม่
crontab -l 2>/dev/null | grep -v "renew_ssl" > /tmp/crontab_new || true

# รันทุกวันที่ 1 และ 15 ของเดือน เวลา 03:00
echo "0 3 1,15 * * /bin/bash /opt/stockradar/renew_ssl.sh" >> /tmp/crontab_new
crontab /tmp/crontab_new
rm /tmp/crontab_new

echo "✅ Cron job ตั้งค่าแล้ว"
echo ""
echo "📋 Cron jobs ที่มีอยู่:"
crontab -l
echo ""

# ทดสอบ renew (dry run — ไม่ได้ renew จริง)
echo "🧪 ทดสอบ certbot renewal (dry-run)..."
systemctl stop nginx
certbot renew --standalone --dry-run 2>&1 | tail -5
systemctl start nginx

echo ""
echo "✅ Auto-Renew ตั้งค่าเสร็จสมบูรณ์!"
echo "📅 จะ renew อัตโนมัติทุกวันที่ 1 และ 15 ของเดือน เวลา 03:00"
echo "📋 ดู log ได้ที่: /var/log/letsencrypt/renew_ssl.log"
