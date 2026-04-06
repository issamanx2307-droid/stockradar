import os
import django
import pandas as pd
import numpy as np

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stockradar.settings")
django.setup()

from radar.models import Symbol, PriceDaily, Indicator
from radar.indicator_cache import cached_load_latest_indicators, cached_load_latest_prices

def debug_scanner():
    sym_qs = Symbol.objects.all()
    symbol_ids = list(sym_qs.values_list("id", flat=True))
    print(f"Total symbol IDs: {len(symbol_ids)}")

    ind_df = cached_load_latest_indicators(symbol_ids)
    print(f"Latest Indicators found: {len(ind_df)}")
    
    price_lat = cached_load_latest_prices(symbol_ids)
    print(f"Latest Prices found: {len(price_lat)}")

    if not price_lat.empty:
        print("\nSample price_lat:")
        print(price_lat.head())

    df = (price_lat
          .merge(ind_df,  on="symbol_id", how="left"))
    
    print(f"\nMerged DF rows: {len(df)}")
    
    if not df.empty:
        # Fillna as in views.py
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        print("Sample merged df:")
        print(df.head())

if __name__ == "__main__":
    debug_scanner()
