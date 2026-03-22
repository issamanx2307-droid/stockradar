"""
portfolio_engine/portfolio_manager.py
จัดการ Portfolio — positions, cash, P/L, sizing
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    symbol:      str
    entry_price: float
    quantity:    int
    stop_loss:   float = 0.0
    decision:    str   = "BUY"


class PortfolioManager:
    def __init__(self, capital: float):
        self.capital   = capital
        self.cash      = capital
        self.positions: list[Position] = []

    def add_position(self, symbol: str, price: float,
                     quantity: int, stop_loss: float = 0.0,
                     decision: str = "BUY") -> str:
        cost = price * quantity
        if cost > self.cash:
            return f"Not enough cash (need {cost:,.0f}, have {self.cash:,.0f})"
        self.positions.append(Position(
            symbol=symbol, entry_price=price,
            quantity=quantity, stop_loss=stop_loss, decision=decision
        ))
        self.cash -= cost
        return "Position added"

    def remove_position(self, symbol: str, price: float) -> dict:
        for i, pos in enumerate(self.positions):
            if pos.symbol == symbol:
                proceeds = price * pos.quantity
                pnl = proceeds - pos.entry_price * pos.quantity
                pnl_pct = pnl / (pos.entry_price * pos.quantity) * 100
                self.cash += proceeds
                self.positions.pop(i)
                return {"symbol": symbol, "pnl": round(pnl, 2),
                        "pnl_pct": round(pnl_pct, 2)}
        return {"error": f"ไม่พบ {symbol} ใน portfolio"}

    def calculate_value(self, market_prices: dict) -> float:
        total = self.cash
        for pos in self.positions:
            px = market_prices.get(pos.symbol, pos.entry_price)
            total += px * pos.quantity
        return round(total, 2)

    def summary(self, market_prices: dict) -> dict:
        total_value  = self.calculate_value(market_prices)
        invested     = sum(p.entry_price * p.quantity for p in self.positions)
        current_mkt  = sum(market_prices.get(p.symbol, p.entry_price) * p.quantity
                           for p in self.positions)
        unrealized   = current_mkt - invested
        return_pct   = (total_value - self.capital) / self.capital * 100

        return {
            "capital":       self.capital,
            "cash":          round(self.cash, 2),
            "invested":      round(invested, 2),
            "market_value":  round(current_mkt, 2),
            "total_value":   total_value,
            "unrealized_pnl":round(unrealized, 2),
            "return_pct":    round(return_pct, 2),
            "positions":     len(self.positions),
        }

    def to_dict(self) -> dict:
        return {
            "capital":   self.capital,
            "cash":      self.cash,
            "positions": [
                {"symbol": p.symbol, "entry_price": p.entry_price,
                 "quantity": p.quantity, "stop_loss": p.stop_loss,
                 "decision": p.decision}
                for p in self.positions
            ],
        }


def run_portfolio_system(
    stock_analysis: list[dict],
    portfolio: PortfolioManager,
    min_score: float = 60,
) -> list[dict]:
    """
    รัน portfolio allocation จาก analyze results
    เรียง score สูงสุดก่อน แล้วซื้อ BUY/STRONG BUY ตามลำดับ
    """
    from decision_engine.decision import calculate_position_size

    # เรียง score สูงสุดก่อน
    ranked = sorted(
        [s for s in stock_analysis if s.get("score", 0) >= min_score],
        key=lambda x: x["score"], reverse=True
    )

    decisions = []
    for stock in ranked:
        if stock.get("decision") not in ("BUY", "STRONG BUY"):
            continue

        entry     = stock["entry"]
        stop_loss = stock.get("stop_loss", entry * 0.95)
        size      = calculate_position_size(
            portfolio.cash, 0.01, entry, stop_loss
        )
        if size <= 0:
            continue

        result = portfolio.add_position(
            symbol   = stock["symbol"],
            price    = entry,
            quantity = size,
            stop_loss= stop_loss,
            decision = stock["decision"],
        )

        decisions.append({
            "symbol":   stock["symbol"],
            "action":   "BUY",
            "score":    stock["score"],
            "decision": stock["decision"],
            "entry":    entry,
            "stop_loss":stop_loss,
            "size":     size,
            "cost":     round(size * entry, 2),
            "result":   result,
        })

    return decisions
