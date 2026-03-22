"""
คำสั่ง Django สำหรับรัน Backtest จาก Terminal

การใช้งาน:
    python manage.py run_backtest --symbol PTT
    python manage.py run_backtest --symbol AAPL --mode sltp --sl 5 --tp 10
    python manage.py run_backtest --symbol KBANK --start 2024-01-01 --end 2024-12-31
    python manage.py run_backtest --symbol PTT --capital 500000 --mode both
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand, CommandError
from radar.backtest_engine import BacktestConfig, run_backtest


class Command(BaseCommand):
    help = "รัน Backtest ทดสอบ Strategy ย้อนหลัง"

    def add_arguments(self, parser):
        parser.add_argument("--symbol",  required=True, help="รหัสหุ้น เช่น PTT, AAPL")
        parser.add_argument("--mode",    default="both", choices=["signal","sltp","both"])
        parser.add_argument("--start",   default=None,  help="วันเริ่มต้น YYYY-MM-DD")
        parser.add_argument("--end",     default=None,  help="วันสิ้นสุด YYYY-MM-DD")
        parser.add_argument("--capital", type=float, default=100_000, help="เงินทุนเริ่มต้น")
        parser.add_argument("--sl",      type=float, default=5.0,  help="Stop Loss %%")
        parser.add_argument("--tp",      type=float, default=10.0, help="Take Profit %%")
        parser.add_argument("--commission", type=float, default=0.15, help="ค่านายหน้า %%")

    def handle(self, *args, **options):
        symbol = options["symbol"].upper()
        end_date   = date.fromisoformat(options["end"])   if options["end"]   else date.today()
        start_date = date.fromisoformat(options["start"]) if options["start"] else end_date - timedelta(days=365)

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== Backtest {symbol} | {start_date} → {end_date} | mode={options['mode']} ==="
        ))

        cfg = BacktestConfig(
            symbol          = symbol,
            start_date      = start_date,
            end_date        = end_date,
            initial_capital = options["capital"],
            mode            = options["mode"],
            stop_loss       = options["sl"],
            take_profit     = options["tp"],
            commission      = options["commission"],
        )

        try:
            results = run_backtest(cfg)
        except ValueError as e:
            raise CommandError(str(e))

        for mode, r in results.items():
            self._print_result(mode, r)

    def _print_result(self, mode: str, r: dict):
        label = "📊 Signal Mode" if mode == "signal" else "🎯 SL/TP Mode"
        ret_color = self.style.SUCCESS if r["total_return"] >= 0 else self.style.ERROR

        self.stdout.write(f"\n{'='*55}")
        self.stdout.write(f" {label}")
        self.stdout.write(f"{'='*55}")
        self.stdout.write(f"  💰 เงินทุนเริ่มต้น:   {r['initial_capital']:>12,.0f} บาท")
        self.stdout.write(f"  💵 เงินทุนสุดท้าย:   {r['final_capital']:>12,.2f} บาท")
        self.stdout.write(ret_color(
            f"  📈 กำไร/ขาดทุน:      {r['total_return_thb']:>+12,.2f} บาท ({r['total_return']:+.2f}%)"
        ))
        self.stdout.write(f"  📊 Buy & Hold:       {r['buy_hold_return']:>+11.2f}%")
        self.stdout.write(f"")
        self.stdout.write(f"  🔢 จำนวน Trade:      {r['total_trades']:>5}")
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ ชนะ:              {r['win_trades']:>5} ({r['win_rate']:.1f}%)"
        ))
        self.stdout.write(self.style.ERROR(
            f"  ❌ แพ้:              {r['loss_trades']:>5}"
        ))
        self.stdout.write(f"  📈 กำไรเฉลี่ย/trade: {r['avg_win']:>+10.2f}%")
        self.stdout.write(f"  📉 ขาดทุนเฉลี่ย/trade:{r['avg_loss']:>+10.2f}%")
        self.stdout.write(f"  ⚖️  Profit Factor:   {r['profit_factor']:>10.2f}")
        self.stdout.write(f"")
        self.stdout.write(self.style.WARNING(
            f"  📉 Max Drawdown:     {r['max_drawdown']:>10.2f}%"
        ))
        self.stdout.write(f"  📐 Sharpe Ratio:     {r['sharpe_ratio']:>10.2f}")
        self.stdout.write(f"  📊 Volatility:       {r['volatility']:>10.2f}%")
        self.stdout.write(f"")

        # Top 5 trades
        if r["trades"]:
            self.stdout.write("  🏆 Trade Log (5 รายการล่าสุด):")
            for t in r["trades"][-5:]:
                emoji  = "✅" if t["is_win"] else "❌"
                reason = t["exit_reason"]
                self.stdout.write(
                    f"    {emoji} {t['entry_date']} → {t['exit_date']} "
                    f"| {t['pnl_pct']:+.2f}% | {t['pnl']:+,.2f}฿ | {reason}"
                )
