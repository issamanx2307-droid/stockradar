"""
subscription.py — Plan definitions + limit checker for StockRadar
"""

PLANS = {
    "free": {
        "name":            "Free",
        "name_th":         "ฟรี",
        "icon":            "🆓",
        "price_thb":       0,
        "price_label":     "ฟรีตลอดกาล",
        "color":           "#78909c",
        "watchlist_limit": 3,
        "signal_days":     7,
        "fundamental_per_day": 5,
        "engine_scan_top": 5,
        "backtest":        False,
        "portfolio_engine":False,
        "scanner_formula": False,
        "features": [
            "Watchlist 3 หุ้น",
            "สัญญาณ 7 วัน",
            "Fundamental 5 ครั้ง/วัน",
            "Top Opportunities Top 5",
            "Economic Calendar",
            "ปฏิทินเศรษฐกิจ",
        ],
    },
    "pro": {
        "name":            "Pro",
        "name_th":         "โปร",
        "icon":            "⭐",
        "price_thb":       299,
        "price_label":     "฿299 / เดือน",
        "color":           "#00d4ff",
        "watchlist_limit": 10,
        "signal_days":     30,
        "fundamental_per_day": -1,   # unlimited
        "engine_scan_top": 50,
        "backtest":        True,
        "portfolio_engine":True,
        "scanner_formula": True,
        "features": [
            "ทุกอย่างใน Free",
            "Watchlist 10 หุ้น",
            "สัญญาณ 30 วัน",
            "Fundamental ไม่จำกัด",
            "Top Opportunities Top 50",
            "Backtest Engine",
            "Portfolio Engine",
            "Scanner Formula Builder",
        ],
    },
    "premium": {
        "name":            "Premium",
        "name_th":         "พรีเมียม",
        "icon":            "💎",
        "price_thb":       599,
        "price_label":     "฿599 / เดือน",
        "color":           "#ffd600",
        "watchlist_limit": 10,
        "signal_days":     90,
        "fundamental_per_day": -1,
        "engine_scan_top": -1,       # unlimited
        "backtest":        True,
        "portfolio_engine":True,
        "scanner_formula": True,
        "features": [
            "ทุกอย่างใน Pro",
            "สัญญาณ 90 วัน",
            "Top Opportunities ไม่จำกัด",
            "Priority Support",
            "Early Access Feature",
        ],
    },
}


def get_plan(plan_key: str) -> dict:
    return PLANS.get(plan_key, PLANS["free"])


def get_user_plan(user) -> dict:
    """ดึง plan ของ user จาก Profile.tier"""
    try:
        if not user or not user.is_authenticated:
            return PLANS["free"]
        tier = user.profile.tier.lower()    # FREE / PRO / PREMIUM
        if tier == "premium":
            return PLANS["premium"]
        elif tier == "pro":
            return PLANS["pro"]
        else:
            return PLANS["free"]
    except Exception:
        return PLANS["free"]


def check_limit(user, feature: str) -> dict:
    """
    ตรวจสอบว่า user มีสิทธิ์ใช้ feature นี้ไหม
    คืน: {"allowed": bool, "limit": any, "plan": str, "upgrade_to": str|None}
    """
    plan_data = get_user_plan(user)
    plan_key  = plan_data.get("name", "Free").lower()

    val = plan_data.get(feature)
    allowed = val is True or (isinstance(val, int) and val != 0)

    upgrade_to = None
    if not allowed:
        if plan_key == "free":
            upgrade_to = "pro"
        elif plan_key == "pro":
            upgrade_to = "premium"

    return {
        "allowed":    allowed,
        "limit":      val,
        "plan":       plan_key,
        "plan_name":  plan_data.get("name_th", "ฟรี"),
        "upgrade_to": upgrade_to,
    }
