#!/bin/bash
# status.sh — ดูสถานะ services ทั้งหมดของ StockRadar
# รัน: bash /opt/stockradar/status.sh

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  StockRadar — Service Status${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ฟังก์ชันตรวจสอบ service
check_service() {
  local name=$1
  local label=$2
  local status=$(systemctl is-active "$name" 2>/dev/null)
  local enabled=$(systemctl is-enabled "$name" 2>/dev/null)

  if [ "$status" = "active" ]; then
    echo -e "  ${GREEN}●${NC} $label"
    echo -e "    Status : ${GREEN}$status${NC} | Auto-start: $enabled"
    # แสดง uptime
    local since=$(systemctl show "$name" --property=ActiveEnterTimestamp --value 2>/dev/null | cut -d' ' -f1-3)
    echo -e "    Since  : $since"
  else
    echo -e "  ${RED}●${NC} $label"
    echo -e "    Status : ${RED}$status${NC} | Auto-start: $enabled"
    echo -e "    ${YELLOW}→ ดู log: journalctl -u $name -n 30${NC}"
  fi
  echo ""
}

check_service "redis-server"           "Redis (Broker + Cache)"
check_service "stockradar"             "Django / Daphne ASGI"
check_service "stockradar-celery"      "Celery Worker"
check_service "stockradar-celerybeat"  "Celery Beat (Scheduler)"
check_service "nginx"                  "Nginx (Reverse Proxy)"

# ── ตรวจสอบ Disk และ Memory ────────────────────────────────
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  ทรัพยากร VPS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  💾 Disk:"
df -h / | tail -1 | awk '{printf "    ใช้: %s / %s (%s)\n", $3, $2, $5}'
echo ""
echo "  🧠 Memory:"
free -h | grep Mem | awk '{printf "    ใช้: %s / %s\n", $3, $2}'
echo ""

# ── ทดสอบ API ─────────────────────────────────────────────
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  ทดสอบ API Endpoint${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 https://radarhoon.com/api/dashboard/ 2>/dev/null || echo "ERR")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "401" ]; then
  echo -e "  ${GREEN}✅ https://radarhoon.com/api/dashboard/ → HTTP $HTTP_CODE${NC}"
else
  echo -e "  ${RED}❌ https://radarhoon.com/api/dashboard/ → $HTTP_CODE${NC}"
fi

# ── ตรวจสอบ scheduled tasks ───────────────────────────────
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  Scheduled Tasks (Celery Beat)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  🕕 18:00 จ-ศ — โหลดราคาหุ้นรายวัน"
echo "  🕡 18:30 จ-ศ — คำนวณ Indicators"
echo "  🕖 19:00 จ-ศ — สร้าง Signals"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
