"""engine_api/urls.py"""
from django.urls import path
from . import views

urlpatterns = [
    path("scan/",              views.scan_stocks,    name="engine-scan"),
    path("analyze/<str:symbol>/", views.analyze_stock, name="engine-analyze"),
    path("backtest/",          views.run_backtest,   name="engine-backtest"),
    path("portfolio/run/",     views.run_portfolio,  name="engine-portfolio"),
]
