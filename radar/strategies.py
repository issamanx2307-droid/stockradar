"""
Unified Strategy Engine
=======================
ศูนย์รวมตรรกะสัญญาณ (Strategy Logic)
สำหรับใช้ทั้งใน Scanner และ Backtester
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

import pandas as pd
import numpy as np

from radar.formula_parser import parser

logger = logging.getLogger(__name__)

@dataclass
class StrategyCondition:
    """เงื่อนไขเดียวในกลยุทธ์"""
    name:     str
    formula:  str    # เช่น "close > ema(200)"
    weight:   float = 1.0
    is_entry: bool  = True  # เงื่อนไขเข้าซื้อ (Long)
    is_exit:  bool  = False # เงื่อนไขขาย (Exit)

@dataclass
class Strategy:
    """กลยุทธ์การลงทุน"""
    name:        str
    description: str = ""
    conditions:  List[StrategyCondition] = field(default_factory=list)
    min_score:   float = 60.0

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        รันกลยุทธ์กับ DataFrame
        คืนค่า DataFrame ที่มีคอลัมน์ 'score', 'signal', 'direction'
        """
        if df.empty:
            return df

        # คำนวณแต่ละเงื่อนไข
        scores = pd.Series(0.0, index=df.index)
        entry_mask = pd.Series(True, index=df.index) # ทุกเงื่อนไขต้องผ่าน (AND)

        for cond in self.conditions:
            try:
                mask = parser.evaluate(df, cond.formula)
                if cond.is_entry:
                    entry_mask &= mask
                    scores += (mask.astype(float) * cond.weight * 10) # ฐานคะแนน
            except Exception as e:
                logger.error("เกิดข้อผิดพลาดในการคำนวณเงื่อนไข '%s': %s", cond.name, e)

        # ปรับคะแนนให้อยู่ใน 0-100
        total_weight = sum(c.weight for c in self.conditions if c.is_entry)
        if total_weight > 0:
            scores = (scores / (total_weight * 10)) * 100
        else:
            scores = pd.Series(0.0, index=df.index)

        # ตัดเกรด
        df = df.copy()
        df['score'] = scores.round(2)
        df['is_entry'] = entry_mask
        df['direction'] = np.where(entry_mask & (scores >= self.min_score), 'LONG', 'NEUTRAL')
        df['signal_type'] = np.where(entry_mask & (scores >= self.min_score), self.name, '')

        return df

# ─── กลยุทธ์พื้นฐาน (Built-in) ────────────────────────────────────────────────

def get_default_strategies() -> Dict[str, Strategy]:
    """คืนกลยุทธ์พื้นฐานที่มากับระบบ"""
    return {
        "GOLDEN_CROSS": Strategy(
            name="GOLDEN_CROSS",
            conditions=[
                StrategyCondition("EMA Cross", "ema(50) > ema(200)"),
                StrategyCondition("Price Above EMA", "close > ema(200)"),
                StrategyCondition("Volume Support", "volume > volume_avg(20)"),
            ],
            min_score=70.0
        ),
        "RSI_OVERSOLD": Strategy(
            name="OVERSOLD",
            conditions=[
                StrategyCondition("Oversold", "rsi(14) < 30"),
                StrategyCondition("Above Long-term Trend", "close > ema(200)"),
            ],
            min_score=60.0
        ),
        "BREAKOUT": Strategy(
            name="BREAKOUT",
            conditions=[
                StrategyCondition("New High", "close > hh(20)"),
                StrategyCondition("Volume Spike", "volume > volume_avg(20) * 1.5"),
            ],
            min_score=75.0
        )
    }

def run_strategy_scan(df: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    """รันกลยุทธ์ที่ระบุกับ DataFrame"""
    strategies = get_default_strategies()
    strat = strategies.get(strategy_name)
    if not strat:
        raise ValueError(f"ไม่พบกลยุทธ์: {strategy_name}")
    return strat.apply(df)
