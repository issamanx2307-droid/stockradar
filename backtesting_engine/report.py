"""
backtesting_engine/report.py
Backtest engine + metrics + report generator
"""
import numpy as np
import pandas as pd


def run_backtest(df: pd.DataFrame, initial_capital: float = 100_000,
                 stop_loss_pct: float = 5.0, take_profit_pct: float = 10.0) -> list[float]:
    """
    Simple signal-based backtest
    คืน equity curve list
    """
    from scanner_engine.scanner import scan_stock
    from scoring_engine.scoring import calculate_score
    from decision_engine.decision import make_decision

    capital    = initial_capital
    cash       = capital
    position   = 0
    entry_price= 0.0
    equity     = [capital]

    for i in range(30, len(df)):
        window = df.iloc[:i]
        close  = float(df["close"].iloc[i])

        # ── Stop loss / Take profit ──
        if position > 0:
            change_pct = (close - entry_price) / entry_price * 100
            if change_pct <= -stop_loss_pct or change_pct >= take_profit_pct:
                cash += position * close
                position = 0
                entry_price = 0.0

        # ── Signal ──
        try:
            signals    = scan_stock(window)
            score_data = calculate_score(signals)
            decision   = make_decision(score_data["total_score"])
        except Exception:
            equity.append(cash + position * close)
            continue

        if decision in ("BUY", "STRONG BUY") and position == 0 and cash > close:
            shares   = int(cash * 0.95 / close)
            cost     = shares * close
            cash    -= cost
            position = shares
            entry_price = close

        elif decision == "SELL" and position > 0:
            cash    += position * close
            position = 0
            entry_price = 0.0

        equity.append(cash + position * close)

    return equity


def calculate_metrics(equity: list[float]) -> dict:
    """คำนวณ performance metrics จาก equity curve"""
    if not equity or len(equity) < 2:
        return {}

    eq  = np.array(equity, dtype=float)
    ret = np.diff(eq) / eq[:-1]

    total_return = (eq[-1] - eq[0]) / eq[0]

    # Max Drawdown
    peak = np.maximum.accumulate(eq)
    dd   = (eq - peak) / peak
    max_drawdown = float(dd.min())

    # Win Rate
    wins     = int((ret > 0).sum())
    total_tr = int((ret != 0).sum())
    win_rate = wins / total_tr if total_tr > 0 else 0.0

    # Sharpe Ratio (annualized, daily returns)
    if ret.std() > 0:
        sharpe = float((ret.mean() / ret.std()) * np.sqrt(252))
    else:
        sharpe = 0.0

    # Profit Factor
    gross_profit = float(ret[ret > 0].sum())
    gross_loss   = float(abs(ret[ret < 0].sum()))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    return {
        "total_return":  round(total_return, 4),
        "win_rate":      round(win_rate, 4),
        "max_drawdown":  round(max_drawdown, 4),
        "sharpe":        round(sharpe, 2),
        "profit_factor": round(profit_factor, 2),
        "total_trades":  total_tr,
        "winning_trades":wins,
        "final_equity":  round(float(eq[-1]), 2),
    }


def generate_report(metrics: dict) -> dict:
    """แปลง metrics → human-readable report"""
    if not metrics:
        return {"error": "ไม่มีข้อมูล metrics"}

    pf = metrics.get("profit_factor", 0)
    pf_str = f"{pf:.2f}" if pf != float("inf") else "∞"

    return {
        "Total Return":   f"{metrics['total_return']*100:.2f}%",
        "Win Rate":       f"{metrics['win_rate']*100:.2f}%",
        "Max Drawdown":   f"{metrics['max_drawdown']*100:.2f}%",
        "Sharpe Ratio":   round(metrics["sharpe"], 2),
        "Profit Factor":  pf_str,
        "Total Trades":   metrics.get("total_trades", 0),
        "Winning Trades": metrics.get("winning_trades", 0),
        "Final Equity":   f"{metrics.get('final_equity', 0):,.2f}",
    }
