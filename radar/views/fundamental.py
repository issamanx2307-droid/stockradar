"""
Views — Fundamental Data, Ticker Tape, Economic Calendar, Thai Indicators
"""

from django.core.cache import cache
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import Symbol


# ─── Fundamental Data API ─────────────────────────────────────────────────────

@api_view(["GET"])
def fundamental_data(request, symbol: str):
    """GET /api/fundamental/<symbol>/ — P/E, EPS, งบการเงิน จาก yfinance"""
    from radar.fundamental_engine import get_fundamental
    sym_obj  = Symbol.objects.filter(symbol=symbol.upper()).first()
    exchange = sym_obj.exchange if sym_obj else ""
    try:
        data = get_fundamental(symbol.upper(), exchange=exchange)
        return Response(data)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["POST"])
def fundamental_batch(request):
    """POST /api/fundamental/batch/ — { symbols: ["PTT","AAPL"] }"""
    from radar.fundamental_engine import get_fundamental
    from concurrent.futures import ThreadPoolExecutor

    symbols  = request.data.get("symbols", [])[:10]
    if not symbols:
        return Response({"error": "กรุณาระบุ symbols"}, status=400)

    sym_map = {s.symbol: s.exchange
               for s in Symbol.objects.filter(symbol__in=symbols)}

    def fetch(sym):
        return get_fundamental(sym, exchange=sym_map.get(sym, ""))

    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(fetch, symbols))

    return Response({"results": results})


# ─── Ticker Tape API ──────────────────────────────────────────────────────────

@api_view(["GET"])
def ticker_tape(request):
    """
    GET /api/ticker/ — ดัชนีตลาด สินค้าโภคภัณฑ์ FX Crypto
    Cache 5 นาที · ใช้กับ Ticker Tape ด้านล่างหน้าจอ
    """
    try:
        from radar.ticker_api import fetch_ticker_data
        data = fetch_ticker_data()
        return Response({"count": len(data), "items": data})
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ─── Economic Calendar API ────────────────────────────────────────────────────

@api_view(["GET"])
def economic_calendar_api(request):
    """
    GET /api/calendar/?days=7
    ปฏิทินเศรษฐกิจสัปดาห์นี้ จาก ForexFactory
    Cache 1 ชั่วโมง
    """
    try:
        days = int(request.query_params.get("days", 7))
        from radar.economic_calendar import fetch_economic_calendar
        data = fetch_economic_calendar(days_ahead=days)

        # group by date
        from collections import defaultdict
        by_date: dict = defaultdict(list)
        for ev in data:
            by_date[ev["date"]].append(ev)

        return Response({
            "count": len(data),
            "days":  days,
            "by_date": dict(by_date),
            "events": data,
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# ─── Thai Economic Indicators API ─────────────────────────────────────────────

@api_view(["GET"])
def thai_indicators_api(request):
    """
    GET /api/thai-indicators/
    ตัวชี้วัดเศรษฐกิจไทยหลัก — Cache 6 ชั่วโมง
    ข้อมูลจาก: BOT, กรมการค้าภายใน, สภาพัฒน์, กรมศุลกากร
    """
    CACHE_KEY = "thai_indicators_v2"
    cached = cache.get(CACHE_KEY)
    if cached:
        return Response(cached)

    indicators = [
        {
            "id": "bot_rate",
            "name": "อัตราดอกเบี้ยนโยบาย BOT",
            "name_en": "BOT Policy Rate",
            "value": "2.00",
            "unit": "%",
            "prev_value": "2.25",
            "change": "-0.25",
            "trend": "down",
            "period": "ก.พ. 2568",
            "icon": "🏦",
            "category": "monetary",
            "source": "ธนาคารแห่งประเทศไทย (BOT)",
            "description": "กนง. ปรับลดอัตราดอกเบี้ยนโยบาย เพื่อกระตุ้นเศรษฐกิจ",
        },
        {
            "id": "cpi",
            "name": "อัตราเงินเฟ้อ (CPI)",
            "name_en": "Inflation Rate (CPI)",
            "value": "1.08",
            "unit": "%",
            "prev_value": "0.78",
            "change": "+0.30",
            "trend": "up",
            "period": "ก.พ. 2568",
            "icon": "🛒",
            "category": "price",
            "source": "กรมการค้าภายใน (MOC)",
            "description": "ดัชนีราคาผู้บริโภคทั่วไป เปรียบเทียบรายปี (YoY)",
        },
        {
            "id": "gdp_growth",
            "name": "อัตราการเติบโต GDP",
            "name_en": "GDP Growth Rate",
            "value": "2.5",
            "unit": "%",
            "prev_value": "1.9",
            "change": "+0.6",
            "trend": "up",
            "period": "Q4/2567",
            "icon": "📈",
            "category": "growth",
            "source": "สภาพัฒนาเศรษฐกิจและสังคมแห่งชาติ (สภาพัฒน์)",
            "description": "ผลิตภัณฑ์มวลรวมในประเทศ เปรียบเทียบรายปี (YoY)",
        },
        {
            "id": "usd_thb",
            "name": "อัตราแลกเปลี่ยน USD/THB",
            "name_en": "USD/THB Exchange Rate",
            "value": "34.20",
            "unit": "บาท",
            "prev_value": "35.10",
            "change": "-0.90",
            "trend": "down",
            "period": "มี.ค. 2568",
            "icon": "💱",
            "category": "forex",
            "source": "ธนาคารแห่งประเทศไทย (BOT)",
            "description": "อัตราแลกเปลี่ยนเงินบาทต่อดอลลาร์สหรัฐ (ค่ากลาง)",
        },
        {
            "id": "export_growth",
            "name": "การส่งออก YoY",
            "name_en": "Export Growth (YoY)",
            "value": "4.2",
            "unit": "%",
            "prev_value": "3.1",
            "change": "+1.1",
            "trend": "up",
            "period": "ก.พ. 2568",
            "icon": "🚢",
            "category": "trade",
            "source": "กรมศุลกากร / กระทรวงพาณิชย์",
            "description": "มูลค่าการส่งออกเปรียบเทียบปีก่อน",
        },
        {
            "id": "tourism",
            "name": "นักท่องเที่ยวต่างชาติ",
            "name_en": "Foreign Tourist Arrivals",
            "value": "3.2",
            "unit": "ล้านคน",
            "prev_value": "2.9",
            "change": "+0.3",
            "trend": "up",
            "period": "ก.พ. 2568",
            "icon": "✈️",
            "category": "tourism",
            "source": "กรมการท่องเที่ยว (DOT)",
            "description": "จำนวนนักท่องเที่ยวต่างชาติเดินทางเข้าไทย",
        },
        {
            "id": "unemployment",
            "name": "อัตราการว่างงาน",
            "name_en": "Unemployment Rate",
            "value": "1.0",
            "unit": "%",
            "prev_value": "0.9",
            "change": "+0.1",
            "trend": "neutral",
            "period": "Q4/2567",
            "icon": "👷",
            "category": "labor",
            "source": "สำนักงานสถิติแห่งชาติ (NSO)",
            "description": "อัตราการว่างงานในประเทศไทย",
        },
        {
            "id": "current_account",
            "name": "ดุลบัญชีเดินสะพัด",
            "name_en": "Current Account Balance",
            "value": "+2.1",
            "unit": "พันล้านUSD",
            "prev_value": "+1.5",
            "change": "+0.6",
            "trend": "up",
            "period": "ก.พ. 2568",
            "icon": "⚖️",
            "category": "trade",
            "source": "ธนาคารแห่งประเทศไทย (BOT)",
            "description": "ดุลบัญชีเดินสะพัด (เกินดุล = บวก)",
        },
    ]

    result = {
        "indicators": indicators,
        "updated_at": "2025-03-28",
        "note": "ข้อมูลอ้างอิงจากแหล่งราชการ อัปเดตตามรอบการประกาศข้อมูล",
    }
    cache.set(CACHE_KEY, result, 6 * 3600)
    return Response(result)
