"""
Radar Formula Parser
====================
แปลงสูตรข้อความ (Scanner Formula) ให้เป็น Pandas Filter Expression
ตัวอย่าง: "close > ema(200) AND rsi(14) < 30"
"""

import re
import pandas as pd
import numpy as np

class FormulaParser:
    """
    Parser สำหรับแปลงสูตรสแกนหุ้นเป็น Pandas query
    """

    # รายชื่อฟังก์ชันที่รองรับ
    SUPPORTED_FUNCTIONS = {
        'ema': 'ema{0}',
        'sma': 'sma{0}',
        'rsi': 'rsi',
        'macd': 'macd',
        'macd_hist': 'macd_hist',
        'atr': 'atr14',
        'adx': 'adx14',
        'volume_avg': 'volume_avg20',
        'hh': 'highest_high_20',
        'll': 'lowest_low_20',
    }

    def __init__(self):
        # แมพชื่อฟิลด์ใน DataFrame
        self.column_map = {
            'close': 'close',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'volume': 'volume',
        }

    def parse(self, formula: str) -> str:
        """
        แปลงสูตรเป็น string ที่ pandas.query() เข้าใจ
        """
        if not formula:
            return ""

        # 1. แปลงตัวดำเนินการตรรกะ
        f = formula.lower()
        f = f.replace(' and ', ' & ').replace(' or ', ' | ').replace(' not ', ' ~ ')

        # 2. แปลงฟังก์ชัน เช่น ema(200) -> ema200
        # ใช้ regex ค้นหา pattern: function_name(number)
        def replace_func(match):
            func_name = match.group(1)
            arg = match.group(2)
            if func_name in self.SUPPORTED_FUNCTIONS:
                template = self.SUPPORTED_FUNCTIONS[func_name]
                return template.format(arg)
            return match.group(0)

        f = re.sub(r'(\w+)\((\d+)\)', replace_func, f)

        # 3. กรณีฟังก์ชันที่ไม่มี argument เช่น rsi() -> rsi
        for func, col in self.SUPPORTED_FUNCTIONS.items():
            if '{0}' not in col:
                f = f.replace(f"{func}()", col)

        # 4. ตรวจสอบความปลอดภัย (เบื้องต้น)
        # อนุญาตเฉพาะตัวอักษร ตัวเลข ช่องว่าง และตัวดำเนินการที่กำหนด
        allowed_chars = re.compile(r'^[a-z0-9\s\(\)\>\<\=\!\&\|\.\_\~\+\-\*\/]+$')
        if not allowed_chars.match(f):
            raise ValueError(f"สูตรมีตัวอักษรที่ไม่ได้รับอนุญาต: {formula}")

        return f

    def evaluate(self, df: pd.DataFrame, formula: str) -> pd.Series:
        """
        รันสูตรกับ DataFrame และคืนค่า Boolean Mask
        """
        try:
            query_str = self.parse(formula)
            # ใช้ eval ของ pandas ซึ่งเร็วกว่า loop
            return df.eval(query_str)
        except Exception as e:
            raise ValueError(f"ไม่สามารถประมวลผลสูตร '{formula}' ได้: {e}")

# Singleton instance
parser = FormulaParser()
