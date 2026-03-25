#!/bin/bash
# ============================================================
# init_data.sh — ติดตั้งทุกอย่างและโหลดข้อมูลเริ่มต้น
# รันครั้งเดียวบน VPS: bash /opt/stockradar/init_data.sh
# ใช้เวลาประมาณ 20-40 นาที (โหลดราคาหุ้น)
# ============================================================
set -e

APP="/opt/stockradar"
VENV="$APP/.venv"
PY="$VENV/bin/python"
MANAGE="$PY $APP/manage.py"
LOG="/var/log/stockradar_init.log"

# ── สีสำหรับ output ──────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

step() { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }
ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
fail() { echo -e "${RED}❌ $1${NC}"; }

echo "" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo "  StockRadar — เริ่มต้นระบบ ($(date '+%Y-%m-%d %H:%M:%S'))" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"

cd "$APP"

# ═══════════════════════════════════════════════════════════
# 1. ติดตั้ง packages ที่ขาด
# ═══════════════════════════════════════════════════════════
step "[1/7] ติดตั้ง Python packages"
source "$VENV/bin/activate"
pip install celery==5.3.6 django-celery-beat==2.6.0 --quiet 2>&1 | tee -a "$LOG"
ok "packages พร้อม"

# ═══════════════════════════════════════════════════════════
# 2. Migrate database
# ═══════════════════════════════════════════════════════════
step "[2/7] Migrate database"
$MANAGE migrate --noinput 2>&1 | tee -a "$LOG"
ok "migrate เสร็จ"

# ═══════════════════════════════════════════════════════════
# 3. ติดตั้ง systemd services (Redis, Celery, Daphne)
# ═══════════════════════════════════════════════════════════
step "[3/7] ติดตั้ง Services (Redis + Celery)"
deactivate
bash "$APP/setup_services.sh" 2>&1 | tee -a "$LOG"
source "$VENV/bin/activate"

# รอ services พร้อม
sleep 3

# ═══════════════════════════════════════════════════════════
# 4. โหลดรายชื่อหุ้น
# ═══════════════════════════════════════════════════════════
step "[4/7] โหลดรายชื่อหุ้น (SET + US)"
$MANAGE load_all_symbols 2>&1 | tee -a "$LOG"
SYMBOL_COUNT=$($MANAGE shell -c "from radar.models import Symbol; print(Symbol.objects.count())" 2>/dev/null || echo "?")
ok "โหลดหุ้นเสร็จ — $SYMBOL_COUNT ตัว"

# ═══════════════════════════════════════════════════════════
# 5. โหลดราคาหุ้น (90 วันล่าสุด)
# ═══════════════════════════════════════════════════════════
step "[5/7] โหลดราคาหุ้น 90 วันล่าสุด (ใช้เวลา 20-40 นาที)"
echo "  โหลดหุ้นไทย (SET) batch=5 delay=3s..." | tee -a "$LOG"
$MANAGE load_prices --exchange SET --days 90 --batch 5 --delay 3 2>&1 | tee -a "$LOG" || warn "SET โหลดบางส่วนล้มเหลว"

echo "  พัก 10 วินาทีก่อนโหลด US..." | tee -a "$LOG"
sleep 10

echo "  โหลดหุ้น US batch=5 delay=3s..." | tee -a "$LOG"
$MANAGE load_prices --exchange US --days 90 --batch 5 --delay 3 2>&1 | tee -a "$LOG" || warn "US โหลดบางส่วนล้มเหลว"

PRICE_COUNT=$($MANAGE shell -c "from radar.models import PriceDaily; print(PriceDaily.objects.count())" 2>/dev/null || echo "?")
ok "โหลดราคาเสร็จ — $PRICE_COUNT แถว"

# ═══════════════════════════════════════════════════════════
# 6. คำนวณ Indicator + สร้าง Signal
# ═══════════════════════════════════════════════════════════
step "[6/7] คำนวณ Indicator + สร้าง Signal"
$MANAGE run_engine 2>&1 | tee -a "$LOG" || warn "engine บางส่วนล้มเหลว"

SIG_COUNT=$($MANAGE shell -c "from radar.models import Signal; print(Signal.objects.count())" 2>/dev/null || echo "?")
ok "สร้าง Signal เสร็จ — $SIG_COUNT สัญญาณ"

# ═══════════════════════════════════════════════════════════
# 7. โหลดข่าว (เรียก API ภายใน)
# ═══════════════════════════════════════════════════════════
step "[7/7] โหลดข่าวตลาด"
$MANAGE shell -c "
try:
    from radar.news_fetcher import fetch_and_save_news
    result = fetch_and_save_news(max_per_feed=30)
    print('ข่าวที่โหลด:', result)
except Exception as e:
    print('ข้ามข่าว:', e)
" 2>&1 | tee -a "$LOG" || warn "โหลดข่าวล้มเหลว (ข้ามได้)"
ok "โหลดข่าวเสร็จ"

deactivate

# ═══════════════════════════════════════════════════════════
# สรุป
# ═══════════════════════════════════════════════════════════
echo "" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
echo -e "${GREEN}  ✅ เสร็จสมบูรณ์! ($(date '+%H:%M:%S'))${NC}" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo "  📊 หุ้น:    $SYMBOL_COUNT ตัว" | tee -a "$LOG"
echo "  💰 ราคา:    $PRICE_COUNT แถว" | tee -a "$LOG"
echo "  📡 Signal:  $SIG_COUNT รายการ" | tee -a "$LOG"
echo "" | tee -a "$LOG"
echo "  🌐 เว็บ: https://radarhoon.com" | tee -a "$LOG"
echo "  📋 Log:  $LOG" | tee -a "$LOG"
echo "  📊 สถานะ: bash /opt/stockradar/status.sh" | tee -a "$LOG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" | tee -a "$LOG"
