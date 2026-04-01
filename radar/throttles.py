from rest_framework.throttling import UserRateThrottle


class ScannerThrottle(UserRateThrottle):
    """จำกัด scanner endpoint — คำนวณหนัก"""
    scope = "scanner"


class BacktestThrottle(UserRateThrottle):
    """จำกัด backtest endpoint — หนักมาก"""
    scope = "backtest"
