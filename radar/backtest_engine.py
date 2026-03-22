"""
Backtest Engine — ทดสอบ Strategy ย้อนหลัง
==========================================
รองรับ 2 แบบ:
  Mode A: Signal Mode  — ซื้อเมื่อ BUY signal, ขายเมื่อ SELL signal
  Mode B: SL/TP Mode   — ซื้อเมื่อเงื่อนไขผ่าน, ขายเมื่อ Stop Loss / Take Profit

สถิติ: Equity Curve, Win Rate, Max Drawdown, Sharpe Ratio, Trade Log
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

import numpy as np
import pandas as pd
from radar.strategies import get_default_strategies, Strategy, StrategyCondition

logger = logging.getLogger(__name__)


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class BacktestConfig:
    """การตั้งค่า Backtest"""
    symbol:          str
    start_date:      date
    end_date:        date
    initial_capital: float = 100_000.0   # เงินทุนเริ่มต้น (บาท)
    mode:            str   = "signal"    # "signal" | "sltp" | "both"
    strategy_name:   Optional[str] = None # ระบุกลยุทธ์ (ถ้ามี)

    # Signal Mode
    buy_signal:  str = "BUY"
    sell_signal: str = "SELL"

    # SL/TP Mode
    stop_loss:   float = 5.0    # % ขาดทุนสูงสุด
    take_profit: float = 10.0   # % กำไรเป้าหมาย

    # Position sizing
    position_pct: float = 100.0   # % ของเงินทุนต่อ 1 trade
    commission:   float = 0.15    # % ค่านายหน้าต่อ trade


@dataclass
class Trade:
    """บันทึกการซื้อขาย 1 รายการ"""
    entry_date:   date
    entry_price:  float
    exit_date:    Optional[date]  = None
    exit_price:   Optional[float] = None
    shares:       float           = 0.0
    pnl:          float           = 0.0    # กำไร/ขาดทุน (บาท)
    pnl_pct:      float           = 0.0    # กำไร/ขาดทุน (%)
    exit_reason:  str             = ""     # "SELL_SIGNAL" | "STOP_LOSS" | "TAKE_PROFIT" | "END"
    is_win:       bool            = False


@dataclass
class BacktestResult:
    """ผลลัพธ์ Backtest ทั้งหมด"""
    symbol:          str
    mode:            str
    start_date:      date
    end_date:        date
    initial_capital: float

    # สถิติหลัก
    final_capital:   float = 0.0
    total_return:    float = 0.0    # % กำไรรวม
    total_return_thb: float = 0.0   # กำไรรวม (บาท)

    # Trade Statistics
    total_trades:    int   = 0
    win_trades:      int   = 0
    loss_trades:     int   = 0
    win_rate:        float = 0.0    # %
    avg_win:         float = 0.0    # % กำไรเฉลี่ยต่อ trade ที่ชนะ
    avg_loss:        float = 0.0    # % ขาดทุนเฉลี่ยต่อ trade ที่แพ้
    profit_factor:   float = 0.0    # รวมกำไร / รวมขาดทุน

    # Risk Statistics
    max_drawdown:    float = 0.0    # % drawdown สูงสุด
    sharpe_ratio:    float = 0.0
    volatility:      float = 0.0    # % std ของ daily returns

    # Equity Curve (date → equity value)
    equity_curve:    list[dict] = field(default_factory=list)

    # Trade Log
    trades:          list[Trade] = field(default_factory=list)

    # ข้อมูลเพิ่มเติม
    bars_in_market:  int   = 0      # วันที่ถือหุ้นอยู่
    total_bars:      int   = 0      # วันซื้อขายทั้งหมด
    buy_hold_return: float = 0.0    # % กำไร Buy & Hold เปรียบเทียบ


# ─── โหลดข้อมูลราคา + indicator ──────────────────────────────────────────────

def _load_price_data(symbol: str, start: date, end: date) -> pd.DataFrame:
    """โหลดราคา + indicator จาก database เป็น DataFrame"""
    from radar.models import PriceDaily, Indicator, Symbol

    try:
        sym_obj = Symbol.objects.get(symbol=symbol.upper())
    except Symbol.DoesNotExist:
        raise ValueError(f"ไม่พบหุ้น '{symbol}' ในฐานข้อมูล")

    prices = list(
        PriceDaily.objects
        .filter(symbol=sym_obj, date__gte=start, date__lte=end)
        .order_by("date")
        .values("date", "open", "high", "low", "close", "volume")
    )
    if not prices:
        raise ValueError(f"ไม่พบข้อมูลราคา {symbol} ในช่วง {start} — {end}")

    df = pd.DataFrame(prices)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    # ดึง indicators
    indicators = list(
        Indicator.objects
        .filter(symbol=sym_obj, date__gte=start, date__lte=end)
        .order_by("date")
        .values("date", "rsi", "ema20", "ema50", "ema200",
                "macd", "macd_signal", "macd_hist",
                "bb_upper", "bb_lower", "volume_avg30")
    )
    if indicators:
        ind_df = pd.DataFrame(indicators)
        for col in ind_df.columns:
            if col != "date":
                ind_df[col] = ind_df[col].astype(float, errors="ignore")
        df = df.merge(ind_df, on="date", how="left")

    return df


def _generate_signals_from_df(df: pd.DataFrame, strategy_name: Optional[str] = None) -> dict:
    """
    สร้าง signals ด้วย Strategy Engine (Vectorized)
    """
    if df.empty:
        return {}

    # เตรียม DataFrame สำหรับ Strategy (เพิ่ม ema50_prev, ema200_prev ถ้าจำเป็น)
    # ใน backtest เรามี history ทั้งหมดอยู่แล้ว สามารถคำนวณ shift ได้เลย
    df = df.sort_values("date").copy()
    df["ema50_prev"]  = df["ema50"].shift(1)
    df["ema200_prev"] = df["ema200"].shift(1)

    # ใช้กลยุทธ์ที่ระบุ หรือใช้ตัวเริ่มต้น
    from radar.strategies import run_strategy_scan, get_default_strategies
    
    if strategy_name:
        res_df = run_strategy_scan(df, strategy_name)
    else:
        # ถ้าไม่ระบุ ให้รันทุกกลยุทธ์แล้วเอามายุบรวมกัน (Simulate default behavior)
        strats = get_default_strategies()
        res_df = df.copy()
        res_df['direction'] = 'NEUTRAL'
        res_df['signal_type'] = ''
        
        for name, strat in strats.items():
            temp = strat.apply(df)
            mask = temp['direction'] != 'NEUTRAL'
            res_df.loc[mask, 'direction'] = temp.loc[mask, 'direction']
            res_df.loc[mask, 'signal_type'] = name

    # แปลงเป็น dict {date: signal_type}
    signals = {}
    for _, row in res_df[res_df['direction'] != 'NEUTRAL'].iterrows():
        d = row['date']
        if hasattr(d, 'date'): d = d.date()
        signals[d] = row['signal_type']
        
    return signals


# ─── Backtest Engine ──────────────────────────────────────────────────────────

def _calc_commission(price: float, shares: float, pct: float) -> float:
    return price * shares * (pct / 100)


def run_signal_mode(df: pd.DataFrame, signals: dict, cfg: BacktestConfig) -> BacktestResult:
    """
    Mode A: ซื้อเมื่อ BUY signal ปรากฏ, ขายเมื่อ SELL signal ปรากฏ
    """
    result = BacktestResult(
        symbol          = cfg.symbol,
        mode            = "signal",
        start_date      = cfg.start_date,
        end_date        = cfg.end_date,
        initial_capital = cfg.initial_capital,
    )

    capital    = cfg.initial_capital
    position   = 0.0    # จำนวนหุ้นที่ถืออยู่
    entry_price = 0.0
    entry_date  = None
    trades: list[Trade] = []
    equity_curve = []
    bars_in_market = 0

    for _, row in df.iterrows():
        d     = row["date"]
        price = float(row["close"])
        sig   = signals.get(d, "")

        # คำนวณ equity ณ วันนี้
        equity = capital + (position * price)
        equity_curve.append({"date": str(d), "equity": round(equity, 2)})

        if position > 0:
            bars_in_market += 1

        # ── ซื้อ
        if sig in ("BUY", "STRONG_BUY", "GOLDEN_CROSS", "OVERSOLD", "BREAKOUT") and position == 0:
            invest  = capital * (cfg.position_pct / 100)
            comm    = _calc_commission(price, invest / price, cfg.commission)
            shares  = (invest - comm) / price
            capital -= (invest)
            position = shares
            entry_price = price
            entry_date  = d

        # ── ขาย
        elif sig in ("SELL", "STRONG_SELL", "DEATH_CROSS", "OVERBOUGHT") and position > 0:
            proceeds = position * price
            comm     = _calc_commission(price, position, cfg.commission)
            capital += proceeds - comm
            pnl      = proceeds - comm - (position * entry_price)
            pnl_pct  = (price - entry_price) / entry_price * 100

            trades.append(Trade(
                entry_date  = entry_date,
                entry_price = entry_price,
                exit_date   = d,
                exit_price  = price,
                shares      = position,
                pnl         = round(pnl, 2),
                pnl_pct     = round(pnl_pct, 2),
                exit_reason = "SELL_SIGNAL",
                is_win      = pnl > 0,
            ))
            position = 0.0

    # ── ปิด position ที่ยังเปิดอยู่ตอนสิ้นสุด
    if position > 0:
        last_price = float(df.iloc[-1]["close"])
        proceeds   = position * last_price
        comm       = _calc_commission(last_price, position, cfg.commission)
        capital   += proceeds - comm
        pnl        = proceeds - comm - (position * entry_price)
        trades.append(Trade(
            entry_date  = entry_date,
            entry_price = entry_price,
            exit_date   = df.iloc[-1]["date"],
            exit_price  = last_price,
            shares      = position,
            pnl         = round(pnl, 2),
            pnl_pct     = round((last_price - entry_price) / entry_price * 100, 2),
            exit_reason = "END",
            is_win      = pnl > 0,
        ))

    result.trades       = trades
    result.equity_curve = equity_curve
    result.bars_in_market = bars_in_market
    result.total_bars   = len(df)
    result.final_capital = round(capital, 2)
    return result


def run_sltp_mode(df: pd.DataFrame, signals: dict, cfg: BacktestConfig) -> BacktestResult:
    """
    Mode B: ซื้อเมื่อ BUY signal, ขายเมื่อ Stop Loss หรือ Take Profit ถึง
    """
    result = BacktestResult(
        symbol          = cfg.symbol,
        mode            = "sltp",
        start_date      = cfg.start_date,
        end_date        = cfg.end_date,
        initial_capital = cfg.initial_capital,
    )

    capital    = cfg.initial_capital
    position   = 0.0
    entry_price = 0.0
    entry_date  = None
    sl_price    = 0.0
    tp_price    = 0.0
    trades: list[Trade] = []
    equity_curve = []
    bars_in_market = 0

    for _, row in df.iterrows():
        d     = row["date"]
        price = float(row["close"])
        high  = float(row["high"])
        low   = float(row["low"])
        sig   = signals.get(d, "")

        equity = capital + (position * price)
        equity_curve.append({"date": str(d), "equity": round(equity, 2)})

        if position > 0:
            bars_in_market += 1
            exit_price  = None
            exit_reason = ""

            # ตรวจ Stop Loss (ใช้ low ของวัน)
            if low <= sl_price:
                exit_price  = sl_price
                exit_reason = "STOP_LOSS"
            # ตรวจ Take Profit (ใช้ high ของวัน)
            elif high >= tp_price:
                exit_price  = tp_price
                exit_reason = "TAKE_PROFIT"

            if exit_price:
                proceeds = position * exit_price
                comm     = _calc_commission(exit_price, position, cfg.commission)
                capital += proceeds - comm
                pnl      = proceeds - comm - (position * entry_price)
                pnl_pct  = (exit_price - entry_price) / entry_price * 100

                trades.append(Trade(
                    entry_date  = entry_date,
                    entry_price = entry_price,
                    exit_date   = d,
                    exit_price  = round(exit_price, 4),
                    shares      = position,
                    pnl         = round(pnl, 2),
                    pnl_pct     = round(pnl_pct, 2),
                    exit_reason = exit_reason,
                    is_win      = pnl > 0,
                ))
                position = 0.0

        # ── ซื้อ (ถ้ายังไม่มี position)
        if sig in ("BUY", "STRONG_BUY", "GOLDEN_CROSS", "OVERSOLD", "BREAKOUT") and position == 0:
            invest      = capital * (cfg.position_pct / 100)
            comm        = _calc_commission(price, invest / price, cfg.commission)
            shares      = (invest - comm) / price
            capital    -= invest
            position    = shares
            entry_price = price
            entry_date  = d
            sl_price    = price * (1 - cfg.stop_loss / 100)
            tp_price    = price * (1 + cfg.take_profit / 100)

    # ── ปิด position ที่ยังเปิดอยู่
    if position > 0:
        last_price = float(df.iloc[-1]["close"])
        proceeds   = position * last_price
        comm       = _calc_commission(last_price, position, cfg.commission)
        capital   += proceeds - comm
        pnl        = proceeds - comm - (position * entry_price)
        trades.append(Trade(
            entry_date  = entry_date,
            entry_price = entry_price,
            exit_date   = df.iloc[-1]["date"],
            exit_price  = last_price,
            shares      = position,
            pnl         = round(pnl, 2),
            pnl_pct     = round((last_price - entry_price) / entry_price * 100, 2),
            exit_reason = "END",
            is_win      = pnl > 0,
        ))

    result.trades        = trades
    result.equity_curve  = equity_curve
    result.bars_in_market = bars_in_market
    result.total_bars    = len(df)
    result.final_capital = round(capital, 2)
    return result


# ─── คำนวณสถิติ ───────────────────────────────────────────────────────────────

def _calc_statistics(result: BacktestResult, df: pd.DataFrame, cfg: BacktestConfig):
    """คำนวณสถิติทั้งหมดใส่ใน result"""
    trades = result.trades

    result.total_return_thb = round(result.final_capital - cfg.initial_capital, 2)
    result.total_return     = round(result.total_return_thb / cfg.initial_capital * 100, 2)

    result.total_trades = len(trades)
    result.win_trades   = sum(1 for t in trades if t.is_win)
    result.loss_trades  = result.total_trades - result.win_trades
    result.win_rate     = round(result.win_trades / result.total_trades * 100, 1) if trades else 0.0

    wins  = [t.pnl_pct for t in trades if t.is_win]
    losses= [t.pnl_pct for t in trades if not t.is_win]

    result.avg_win  = round(sum(wins)   / len(wins),   2) if wins   else 0.0
    result.avg_loss = round(sum(losses) / len(losses), 2) if losses else 0.0

    total_win_amt  = sum(t.pnl for t in trades if t.is_win)
    total_loss_amt = abs(sum(t.pnl for t in trades if not t.is_win))
    result.profit_factor = round(total_win_amt / total_loss_amt, 2) if total_loss_amt > 0 else 0.0

    # Max Drawdown
    if result.equity_curve:
        equities  = [e["equity"] for e in result.equity_curve]
        peak      = equities[0]
        max_dd    = 0.0
        for eq in equities:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown = round(max_dd, 2)

    # Daily Returns สำหรับ Sharpe
    if len(result.equity_curve) > 1:
        equities     = [e["equity"] for e in result.equity_curve]
        daily_returns= [
            (equities[i] - equities[i-1]) / equities[i-1]
            for i in range(1, len(equities))
        ]
        mean_ret = np.mean(daily_returns)
        std_ret  = np.std(daily_returns)
        result.volatility   = round(std_ret * math.sqrt(252) * 100, 2)
        result.sharpe_ratio = round(
            (mean_ret * 252) / (std_ret * math.sqrt(252))
            if std_ret > 0 else 0.0,
            2
        )

    # Buy & Hold Return
    if not df.empty:
        first_price = float(df.iloc[0]["close"])
        last_price  = float(df.iloc[-1]["close"])
        result.buy_hold_return = round((last_price - first_price) / first_price * 100, 2)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def run_backtest(cfg: BacktestConfig) -> dict:
    """
    รัน Backtest ตาม config
    คืน dict สำหรับ JSON API response
    """
    logger.info("เริ่ม Backtest %s | mode=%s | %s → %s",
                cfg.symbol, cfg.mode, cfg.start_date, cfg.end_date)

    # โหลดข้อมูล
    df      = _load_price_data(cfg.symbol, cfg.start_date, cfg.end_date)
    signals = _generate_signals_from_df(df, strategy_name=cfg.strategy_name)

    results = {}

    if cfg.mode in ("signal", "both"):
        r = run_signal_mode(df, signals, cfg)
        _calc_statistics(r, df, cfg)
        results["signal"] = _result_to_dict(r)

    if cfg.mode in ("sltp", "both"):
        r = run_sltp_mode(df, signals, cfg)
        _calc_statistics(r, df, cfg)
        results["sltp"] = _result_to_dict(r)

    logger.info("Backtest %s เสร็จ", cfg.symbol)
    return results


def _result_to_dict(r: BacktestResult) -> dict:
    """แปลง BacktestResult เป็น dict สำหรับ JSON"""
    return {
        "symbol":          r.symbol,
        "mode":            r.mode,
        "start_date":      str(r.start_date),
        "end_date":        str(r.end_date),
        "initial_capital": r.initial_capital,
        "final_capital":   r.final_capital,
        "total_return":    r.total_return,
        "total_return_thb": r.total_return_thb,
        "buy_hold_return": r.buy_hold_return,
        "total_trades":    r.total_trades,
        "win_trades":      r.win_trades,
        "loss_trades":     r.loss_trades,
        "win_rate":        r.win_rate,
        "avg_win":         r.avg_win,
        "avg_loss":        r.avg_loss,
        "profit_factor":   r.profit_factor,
        "max_drawdown":    r.max_drawdown,
        "sharpe_ratio":    r.sharpe_ratio,
        "volatility":      r.volatility,
        "bars_in_market":  r.bars_in_market,
        "total_bars":      r.total_bars,
        "equity_curve":    r.equity_curve,
        "trades": [
            {
                "entry_date":  str(t.entry_date),
                "entry_price": t.entry_price,
                "exit_date":   str(t.exit_date) if t.exit_date else None,
                "exit_price":  t.exit_price,
                "shares":      round(t.shares, 4),
                "pnl":         t.pnl,
                "pnl_pct":     t.pnl_pct,
                "exit_reason": t.exit_reason,
                "is_win":      t.is_win,
            }
            for t in r.trades
        ],
    }
