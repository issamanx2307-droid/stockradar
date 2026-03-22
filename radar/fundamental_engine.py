"""
fundamental_engine.py — ดึง Fundamental Data จาก yfinance
Cache 24 ชั่วโมง เพราะข้อมูลอัปเดตรายไตรมาส
"""
import logging
from datetime import datetime
import yfinance as yf

logger = logging.getLogger(__name__)

CACHE_TTL = 60 * 60 * 24  # 24 hours


def _ticker_symbol(symbol: str, exchange: str = "") -> str:
    """แปลง symbol ให้ถูกต้องสำหรับ yfinance"""
    sym = symbol.upper().strip()
    if exchange in ("SET",) or (not exchange and len(sym) <= 5 and sym.isalpha()):
        if not sym.endswith(".BK"):
            return f"{sym}.BK"
    return sym


def _fmt_num(val, decimals=2, suffix=""):
    """Format ตัวเลขให้อ่านง่าย"""
    if val is None:
        return None
    try:
        v = float(val)
        if abs(v) >= 1e12:
            return f"{v/1e12:.2f}T{suffix}"
        if abs(v) >= 1e9:
            return f"{v/1e9:.2f}B{suffix}"
        if abs(v) >= 1e6:
            return f"{v/1e6:.2f}M{suffix}"
        return round(v, decimals)
    except Exception:
        return val


def _pct(val):
    if val is None:
        return None
    try:
        return round(float(val) * 100, 2)
    except Exception:
        return None


def get_fundamental(symbol: str, exchange: str = "") -> dict:
    """
    ดึง Fundamental Data ทั้งหมด
    คืน dict พร้อมใช้งาน
    """
    from django.core.cache import cache

    cache_key = f"fundamental:{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    ticker_sym = _ticker_symbol(symbol, exchange)

    try:
        t = yf.Ticker(ticker_sym)
        info = t.info or {}

        # งบการเงินรายไตรมาส
        try:
            qf = t.quarterly_financials
            qi = t.quarterly_income_stmt
            qs = []
            if qf is not None and not qf.empty:
                for col in list(qf.columns)[:4]:
                    q = {"period": str(col.date() if hasattr(col,"date") else col)[:10]}
                    for row_key, out_key in [
                        ("Total Revenue", "revenue"),
                        ("Gross Profit", "gross_profit"),
                        ("Net Income", "net_income"),
                        ("Operating Income", "operating_income"),
                        ("EBITDA", "ebitda"),
                    ]:
                        try:
                            v = qf.loc[row_key, col] if row_key in qf.index else None
                            q[out_key] = int(v) if v and str(v) != "nan" else None
                        except Exception:
                            q[out_key] = None
                    qs.append(q)
        except Exception:
            qs = []

        # Analyst recommendations
        try:
            rec = t.recommendations
            analyst_summary = {}
            if rec is not None and not rec.empty:
                latest = rec.iloc[-1] if len(rec) > 0 else None
                if latest is not None:
                    for col in ["strongBuy","buy","hold","sell","strongSell"]:
                        try:
                            analyst_summary[col] = int(latest.get(col, 0))
                        except Exception:
                            analyst_summary[col] = 0
        except Exception:
            analyst_summary = {}

        result = {
            # ── Company Info ──
            "symbol":        symbol,
            "ticker":        ticker_sym,
            "name":          info.get("shortName") or info.get("longName", ""),
            "sector":        info.get("sector", ""),
            "industry":      info.get("industry", ""),
            "country":       info.get("country", ""),
            "website":       info.get("website", ""),
            "description":   (info.get("longBusinessSummary") or "")[:400],
            "employees":     info.get("fullTimeEmployees"),

            # ── Valuation ──
            "pe_trailing":   round(float(info["trailingPE"]), 2) if info.get("trailingPE") else None,
            "pe_forward":    round(float(info["forwardPE"]), 2)  if info.get("forwardPE")  else None,
            "eps":           info.get("trailingEps"),
            "pb_ratio":      round(float(info["priceToBook"]), 2) if info.get("priceToBook") else None,
            "ps_ratio":      round(float(info["priceToSalesTrailing12Months"]), 2) if info.get("priceToSalesTrailing12Months") else None,
            "peg_ratio":     round(float(info["pegRatio"]), 2) if info.get("pegRatio") else None,
            "ev_ebitda":     round(float(info["enterpriseToEbitda"]), 2) if info.get("enterpriseToEbitda") else None,
            "market_cap":    info.get("marketCap"),
            "market_cap_fmt":_fmt_num(info.get("marketCap")),
            "enterprise_value": info.get("enterpriseValue"),

            # ── Dividends ──
            "dividend_yield":   _pct(info.get("dividendYield")),
            "dividend_rate":    info.get("dividendRate"),
            "payout_ratio":     _pct(info.get("payoutRatio")),
            "ex_dividend_date": info.get("exDividendDate"),

            # ── Profitability ──
            "revenue":         info.get("totalRevenue"),
            "revenue_fmt":     _fmt_num(info.get("totalRevenue")),
            "gross_profit":    info.get("grossProfits"),
            "net_income":      info.get("netIncomeToCommon"),
            "net_income_fmt":  _fmt_num(info.get("netIncomeToCommon")),
            "profit_margin":   _pct(info.get("profitMargins")),
            "gross_margin":    _pct(info.get("grossMargins")),
            "operating_margin":_pct(info.get("operatingMargins")),
            "ebitda":          info.get("ebitda"),
            "ebitda_fmt":      _fmt_num(info.get("ebitda")),
            "roe":             _pct(info.get("returnOnEquity")),
            "roa":             _pct(info.get("returnOnAssets")),

            # ── Growth ──
            "revenue_growth":  _pct(info.get("revenueGrowth")),
            "earnings_growth": _pct(info.get("earningsGrowth")),

            # ── Financial Health ──
            "debt_to_equity":  round(float(info["debtToEquity"]), 2) if info.get("debtToEquity") else None,
            "current_ratio":   round(float(info["currentRatio"]), 2) if info.get("currentRatio") else None,
            "quick_ratio":     round(float(info["quickRatio"]), 2) if info.get("quickRatio") else None,
            "operating_cf":    info.get("operatingCashflow"),
            "operating_cf_fmt":_fmt_num(info.get("operatingCashflow")),
            "free_cashflow":   info.get("freeCashflow"),
            "free_cf_fmt":     _fmt_num(info.get("freeCashflow")),

            # ── 52-Week ──
            "week52_high":     info.get("fiftyTwoWeekHigh"),
            "week52_low":      info.get("fiftyTwoWeekLow"),
            "week52_change":   _pct(info.get("52WeekChange")),

            # ── Analyst ──
            "analyst_count":       info.get("numberOfAnalystOpinions"),
            "target_mean_price":   info.get("targetMeanPrice"),
            "target_high_price":   info.get("targetHighPrice"),
            "target_low_price":    info.get("targetLowPrice"),
            "recommendation":      info.get("recommendationKey", "").upper(),
            "analyst_summary":     analyst_summary,

            # ── Quarterly Financials ──
            "quarterly_financials": qs,

            # ── Meta ──
            "fetched_at": datetime.now().isoformat()[:19],
        }

        cache.set(cache_key, result, timeout=CACHE_TTL)
        return result

    except Exception as e:
        logger.error("fundamental fetch error %s: %s", symbol, e)
        return {"symbol": symbol, "error": str(e)}
