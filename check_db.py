import os
import django
import pandas as pd

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockradar.settings")
django.setup()

from radar.models import Symbol, PriceDaily, Indicator, Signal

def check_data():
    print("--- Database Summary ---")
    print(f"Symbols: {Symbol.objects.count()}")
    print(f"Prices:  {PriceDaily.objects.count()}")
    print(f"Indicators: {Indicator.objects.count()}")
    print(f"Signals: {Signal.objects.count()}")
    
    if Symbol.objects.exists():
        print("\n--- Sample Symbols ---")
        for s in Symbol.objects.all()[:5]:
            print(f"{s.symbol} ({s.exchange})")
            
    if PriceDaily.objects.exists():
        print("\n--- Latest Price ---")
        p = PriceDaily.objects.order_by("-date").first()
        print(f"{p.symbol.symbol} | {p.date} | {p.close}")
    else:
        print("\n⚠️ PriceDaily table is EMPTY!")

    if Indicator.objects.exists():
        print("\n--- Latest Indicator ---")
        ind = Indicator.objects.order_by("-date").first()
        print(f"{ind.symbol.symbol} | {ind.date} | RSI={ind.rsi}")
    else:
        print("\n⚠️ Indicator table is EMPTY!")

if __name__ == "__main__":
    check_data()
