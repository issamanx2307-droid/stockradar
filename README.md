# 📡 Radar หุ้น — Stock Radar System

ระบบสแกนและวิเคราะห์หุ้นคล้าย TradingView สร้างด้วย Django + React

---

## 🗂 โครงสร้างโปรเจค

```
stockradar/
├── stockradar/
│   ├── settings.py       # การตั้งค่าระบบ
│   ├── urls.py           # URL หลัก
│   └── celery.py         # Background tasks
├── radar/
│   ├── models.py         # โมเดลฐานข้อมูล
│   ├── admin.py          # Django Admin (ภาษาไทย)
│   ├── tasks.py          # Celery tasks
│   └── management/commands/
│       ├── load_symbols.py   # โหลดรายชื่อหุ้น
│       └── load_prices.py    # โหลดราคาหุ้น
├── frontend/             # React + Vite (Phase 3)
├── requirements.txt
└── .env.example
```

---

## 🚀 เริ่มต้นใช้งาน

### 1. ติดตั้ง Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. ตั้งค่า Environment

```bash
cp .env.example .env
# แก้ไขค่าใน .env ตามต้องการ
```

### 3. สร้างฐานข้อมูล

```bash
python manage.py migrate
```

### 4. สร้าง Admin User

```bash
python manage.py createsuperuser
```

### 5. โหลดรายชื่อหุ้น

```bash
# โหลดหุ้นทั้งหมด (ไทย + US)
python manage.py load_symbols

# โหลดเฉพาะหุ้นไทย SET
python manage.py load_symbols --exchange SET

# โหลดเฉพาะ US
python manage.py load_symbols --exchange US
```

### 6. โหลดราคาหุ้น

```bash
# โหลดทุกหุ้น ย้อนหลัง 1 ปี
python manage.py load_prices

# โหลดเฉพาะหุ้นที่ระบุ
python manage.py load_prices --symbol PTT
python manage.py load_prices --symbol AAPL

# โหลดเฉพาะตลาด
python manage.py load_prices --exchange SET

# โหลดย้อนหลัง 90 วัน
python manage.py load_prices --days 90

# โหลดย้อนหลัง 5 ปี
python manage.py load_prices --full
```

### 7. เปิด Django Server

```bash
python manage.py runserver
```

เปิดเบราว์เซอร์ไปที่: http://localhost:8000/admin

---

## ⚙️ Celery (Background Tasks)

ต้องติดตั้งและเปิด Redis ก่อน

```bash
# Terminal 1: Celery Worker
celery -A stockradar worker --loglevel=info

# Terminal 2: Celery Beat (ตั้งเวลาอัตโนมัติ)
celery -A stockradar beat --loglevel=info
```

### ตารางเวลา (อัตโนมัติ)
| เวลา    | Task                          |
|---------|-------------------------------|
| 18:00 น.| โหลดราคาหุ้นรายวัน             |
| 18:30 น.| คำนวณ EMA, RSI, Volume        |
| 19:00 น.| สร้าง Signal ซื้อ/ขาย          |

---

## 📊 ตัวสแกน Signal ที่รองรับ

| Signal       | เงื่อนไข                         |
|--------------|----------------------------------|
| OVERSOLD     | RSI < 30                         |
| OVERBOUGHT   | RSI > 70                         |
| GOLDEN_CROSS | EMA20 > EMA50 > EMA200           |
| DEATH_CROSS  | EMA20 < EMA50 < EMA200           |
| BREAKOUT     | Volume > ค่าเฉลี่ย 30 วัน × 2   |
| BUY          | ราคา > EMA200 และ RSI > 50       |
| SELL         | ราคา < EMA200 และ RSI < 50       |

---

## 🛠 Phase ถัดไป

- **Phase 2** — Indicator Engine + Signal Engine (คำนวณแบบ batch 10,000 หุ้น)
- **Phase 3** — REST API + React Frontend (ภาษาไทย)
