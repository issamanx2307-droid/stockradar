import pandas as pd
import numpy as np
from radar.formula_parser import parser
from radar.strategies import Strategy, StrategyCondition

def test_parser():
    print("Testing Parser...")
    f1 = "close > ema(200) AND rsi(14) < 30"
    p1 = parser.parse(f1)
    print(f"Formula: {f1} -> {p1}")
    assert "close > ema200 & rsi < 30" in p1.lower()
    
    f2 = "volume > volume_avg(20) * 2"
    p2 = parser.parse(f2)
    print(f"Formula: {f2} -> {p2}")
    assert "volume > volume_avg20 * 2" in p2.lower()
    print("Parser Test Passed!")

def test_strategy():
    print("\nTesting Strategy Engine...")
    df = pd.DataFrame({
        'close': [100, 105, 110],
        'ema200': [90, 90, 90],
        'rsi': [25, 35, 45],
        'volume': [1000, 2000, 1500],
        'volume_avg20': [800, 800, 800]
    })
    
    strat = Strategy(
        name="TEST_STRAT",
        conditions=[
            StrategyCondition("Price > EMA", "close > ema(200)"),
            StrategyCondition("Oversold", "rsi(14) < 40")
        ]
    )
    
    res = strat.apply(df)
    print("Result DataFrame:")
    print(res[['close', 'score', 'direction']])
    
    assert res.iloc[0]['direction'] == 'LONG'
    assert res.iloc[2]['direction'] == 'NEUTRAL'
    print("Strategy Engine Test Passed!")

if __name__ == "__main__":
    try:
        test_parser()
        test_strategy()
        print("\nAll verifications passed!")
    except Exception as e:
        print(f"\nVerification failed: {e}")
