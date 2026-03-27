# StockRadar (radarhoon.com) — บันทึกการทำงาน
อัปเดตล่าสุด: 26 มีนาคม 2569

---

## ✅ เสร็จแล้ว

### Infrastructure
- VPS: Hostinger, IP `187.127.107.228`, Ubuntu 22.04
- Domain: `radarhoon.com` + SSL (Let's Encrypt)
- Nginx: port 80 → 308 redirect → HTTPS ✅
- Django (Daphne ASGI) รันเป็น systemd service ✅
- Database: **PostgreSQL** (เปลี่ยนจาก SQLite) ✅
  - User: `stockradar`, DB: `stockradar`
  - Password: `Radar2025Secure`
  - DATABASE_URL อยู่ใน `/opt/stockradar/.env` + systemd override

### Data Pipeline
- **GitHub Actions** (`.github/workflows/fetch_prices.yml`)
  - รันทุกวันจันทร์-ศุกร์ **17:30 น.** (10:30 UTC)
  - ดึงราคาหุ้นจาก **Stooq** (แทน Yahoo Finance ที่ block VPS)
  - ส่งข้อมูลมา VPS ผ่าน `POST /api/import-prices/`
  - เรียก `POST /api/trigger-engine/` หลังโหลดเสร็จ (run_engine + refresh_snapshot + fetch_news)
- โหลดข้อมูล 5 ปี: **154,241 แถว** อยู่ใน DB แล้ว
- หุ้นทั้งหมด: **238 ตัว** (112 SET + 126 US)
  - Stooq ดึงได้ 123 ตัว / ไม่ได้ 113 ตัว (US stocks บางส่วนไม่มีใน Stooq)

### GitHub Secrets ที่ตั้งไว้
- `VPS_API_URL` = `https://radarhoon.com`
- `VPS_API_TOKEN` = `radar-b9fbfc71b6303628a3d4a788c96787ab`
- `IMPORT_API_TOKEN` ใน `/opt/stockradar/.env` = ค่าเดียวกัน

### Frontend (Landing Page)
- Landing page: `radarhoon.com` ✅
- Ticker tape วิ่งด้านล่าง ✅ (Gold, Oil, Bitcoin, SET, Dow Jones ฯลฯ)
- TOP OPPORTUNITIES box (ซ้าย) — ข้อมูลจาก run_engine

### Admin
- URL: `https://radarhoon.com/admin/`
- Username: `admin`
- Email: `admin@radarhoon.com`

### Management Commands ที่มีจริง
```
load_all_symbols    load_prices        load_set_file
load_symbols        load_us_symbols    refresh_snapshot
run_backtest        run_engine         setup_system
setup_timescaledb   start_scheduler    fetch_news
```

---

## ⏳ ค้างอยู่ / ยังไม่เสร็จ

### 1. ข่าว (News) ไม่แสดงบน Landing Page
- **สาเหตุ**: `news_list` view ไม่มี `@permission_classes([AllowAny])` → block anonymous
- **แก้แล้ว**: commit `d199a22` push แล้ว
- **สิ่งที่ต้องทำ**: รันบน VPS:
  ```bash
  cd /opt/stockradar && git pull && systemctl restart stockradar
  ```

### 2. TOP OPPORTUNITIES ยังไม่แสดงข้อมูล
- มีราคาใน DB แล้ว (154k แถว)
- ต้องรัน:
  ```bash
  cd /opt/stockradar && source .venv/bin/activate
  export DATABASE_URL="postgresql://stockradar:Radar2025Secure@localhost:5432/stockradar"
  python manage.py run_engine
  python manage.py refresh_snapshot
  ```

### 3. หุ้น US 113 ตัวดึงไม่ได้จาก Stooq
- TSLA, AAPL, META, AMZN, MSFT, NVDA ฯลฯ ไม่มีใน Stooq
- ทางออก: เพิ่ม Yahoo Finance เป็น fallback หรือใช้ Alpha Vantage

### 4. Celery Worker/Beat ยังไม่ติดตั้ง
- ต้องรัน: `bash /opt/stockradar/setup_services.sh`
- Celery ใช้สำหรับ task queue (ตอนนี้ใช้ GitHub Actions แทนได้)

### 5. Redis Error
- `redis-server.service failed` — ยังไม่ได้แก้
- กระทบ: Celery ไม่ทำงาน, cache บางส่วน

### 6. User Profile หลัง Login
- เคยพูดถึงแต่ยังไม่ได้ตรวจสอบว่าครบหรือยัง

### 7. STATICFILES_DIRS Warning
- `/opt/stockradar/static` ไม่มี → warning ทุกครั้ง
- แก้: `mkdir -p /opt/stockradar/static`

---

## 🔑 ข้อมูลสำคัญ

### VPS
```
IP: 187.127.107.228
Web Terminal: Hostinger Panel
DB: postgresql://stockradar:Radar2025Secure@localhost:5432/stockradar
IMPORT_API_TOKEN: radar-b9fbfc71b6303628a3d4a788c96787ab
```

### คำสั่งที่ต้องรันทุกครั้งก่อนใช้ manage.py
```bash
cd /opt/stockradar
source .venv/bin/activate
export DATABASE_URL="postgresql://stockradar:Radar2025Secure@localhost:5432/stockradar"
```

### GitHub
```
Repo: https://github.com/issamanx2307-droid/stockradar
Actions: https://github.com/issamanx2307-droid/stockradar/actions
Secrets: https://github.com/issamanx2307-droid/stockradar/settings/secrets/actions
```

---

## 📋 สิ่งที่ต้องทำพรุ่งนี้ (เรียงลำดับ)

1. `git pull && systemctl restart stockradar` → ดูข่าวขึ้นไหม
2. รัน `run_engine + refresh_snapshot` → ดู TOP OPPORTUNITIES
3. แก้ Redis (`systemctl status redis-server`)
4. รัน `setup_services.sh` → ติดตั้ง Celery
5. แก้ US stocks 113 ตัวที่ Stooq ไม่มี
6. ตรวจสอบ User Profile page
