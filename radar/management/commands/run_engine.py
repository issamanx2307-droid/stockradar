"""
run_engine — Pro Version
การใช้งาน:
    python manage.py run_engine                    # ทุก engine (indicators + signals)
    python manage.py run_engine --mode indicators  # แค่ Indicator Engine
    python manage.py run_engine --mode signals     # แค่ Signal Engine (vectorized batch)
    python manage.py run_engine --mode scan        # Quick Scan vectorized
    python manage.py run_engine --exchange SET     # เฉพาะหุ้นไทย
    python manage.py run_engine --symbol PTT       # หุ้นเดียว
    python manage.py run_engine --celery           # ส่ง Celery async
    python manage.py run_engine --min-score 70     # กรองคะแนน
"""

import time
import logging
from django.core.management.base import BaseCommand, CommandError
from radar.models import Symbol

logger = logging.getLogger(__name__)

DIRECTION_EMOJI = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⬜"}
SIGNAL_EMOJI = {
    "GOLDEN_CROSS":"⭐","EMA_ALIGNMENT":"📈","EMA_PULLBACK":"↩️",
    "BREAKOUT":"🚀","BUY":"🟢","STRONG_BUY":"💚","OVERSOLD":"🔵",
    "DEATH_CROSS":"💀","BREAKDOWN":"💥","SELL":"🔴","STRONG_SELL":"❤️",
    "OVERBOUGHT":"🟡","WATCH":"👁️","ALERT":"⚠️",
}


class Command(BaseCommand):
    help = "รัน Indicator Engine + Signal Engine (Pro Vectorized)"

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=["all","indicators","signals","scan"], default="all")
        parser.add_argument("--exchange", type=str, default=None)
        parser.add_argument("--symbol",   type=str, default=None)
        parser.add_argument("--celery",   action="store_true")
        parser.add_argument("--limit",    type=int, default=None)
        parser.add_argument("--min-score",type=float, default=55.0, dest="min_score")
        parser.add_argument("--days",     type=int, default=300)

    def handle(self, *args, **options):
        mode      = options["mode"]
        exchange  = options.get("exchange")
        sym_code  = options.get("symbol")
        use_celery= options["celery"]
        limit     = options.get("limit")
        min_score = options["min_score"]
        days      = options["days"]

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n╔══════════════════════════════════════╗\n"
            f"║  📡 Radar Engine  mode={mode:<10}     ║\n"
            f"╚══════════════════════════════════════╝\n"
        ))

        # ── Single symbol mode ──────────────────────────────────────────────
        if sym_code:
            self._run_single(sym_code.upper(), mode)
            return

        # ── Celery async ────────────────────────────────────────────────────
        if use_celery:
            self._run_celery(mode, exchange)
            return

        # ── Quick Scan (vectorized batch) ───────────────────────────────────
        if mode == "scan":
            self._run_quick_scan(exchange, limit or 10000, min_score)
            return

        # ── Standard mode: เลือกหุ้น ────────────────────────────────────────
        qs = Symbol.objects.all()
        if exchange:
            qs = qs.filter(exchange__in=["NASDAQ","NYSE"]) if exchange.upper()=="US" \
                 else qs.filter(exchange=exchange.upper())
        if limit:
            qs = qs[:limit]
        symbols = list(qs.order_by("symbol"))

        if not symbols:
            self.stdout.write(self.style.WARNING("⚠️  ไม่พบหุ้น"))
            return

        self.stdout.write(f"จำนวนหุ้น: {len(symbols)} ตัว\n")
        t0 = time.perf_counter()

        ind_ok = ind_err = sig_ok = sig_err = sig_count = 0

        for i, sym in enumerate(symbols, 1):
            prog = f"[{i:>4}/{len(symbols)}]"

            # ── Indicator Engine ──────────────────────────────────────────
            if mode in ("all","indicators"):
                try:
                    from radar.indicator_engine import run_indicator_engine
                    r = run_indicator_engine(sym)
                    ind_ok += 1
                    self.stdout.write(f"  {prog} 📊 {sym.symbol:<10} {r['bars']} วัน")
                except Exception as e:
                    ind_err += 1
                    self.stdout.write(self.style.ERROR(f"  {prog} ❌ {sym.symbol} ind: {e}"))

            # ── Signal Engine ─────────────────────────────────────────────
            if mode in ("all","signals"):
                try:
                    from radar.signal_engine import run_signal_engine
                    r = run_signal_engine(sym)
                    sig_ok += 1
                    if r:
                        sig_count += 1
                        de = DIRECTION_EMOJI.get(r["direction"], "⬜")
                        se = SIGNAL_EMOJI.get(r["signal_type"], "⬜")
                        sl = f"SL={r['stop_loss']:.2f}" if r.get("stop_loss") else ""
                        rp = f"Risk={r['risk_pct']:.1f}%" if r.get("risk_pct") else ""
                        self.stdout.write(
                            f"  {prog} {de}{se} {sym.symbol:<10} "
                            f"{r['signal_type']:<15} score={r['score']:.0f} "
                            f"ADX={r.get('adx') or 0:.1f} {sl} {rp}"
                        )
                    else:
                        self.stdout.write(f"  {prog} ⬜ {sym.symbol:<10} ไม่มีสัญญาณ")
                except Exception as e:
                    sig_err += 1
                    self.stdout.write(self.style.ERROR(f"  {prog} ❌ {sym.symbol} sig: {e}"))

        elapsed = time.perf_counter() - t0
        self._print_summary(elapsed, len(symbols), mode, ind_ok, ind_err, sig_ok, sig_err, sig_count)

        # Warm up Redis cache หลัง engine เสร็จ
        if mode in ("all", "signals"):
            self._warmup_cache(exchange)

    # ── Quick Scan (vectorized) ─────────────────────────────────────────────
    def _run_quick_scan(self, exchange, limit, min_score):
        from radar.scanner_engine import run_quick_scan
        from radar.models import Symbol as S

        self.stdout.write(f"⚡ Quick Scan vectorized | limit={limit}\n")
        t0 = time.perf_counter()

        result = run_quick_scan(exchange=exchange, limit=limit)

        elapsed = time.perf_counter() - t0

        self.stdout.write(self.style.SUCCESS(
            f"\n╔══════════════════════════════════════════╗\n"
            f"║  ✅ Quick Scan สรุป                       ║\n"
            f"╠══════════════════════════════════════════╣\n"
            f"║  สแกน:    {result['scanned']:>6} หุ้น                  ║\n"
            f"║  Signal:  {result['signals']:>6} รายการ               ║\n"
            f"║  เวลา:    {elapsed:>6.2f} วินาที               ║\n"
            f"║  เฉลี่ย:  {result.get('per_stock_ms',0):>6.1f} ms/หุ้น             ║\n"
            f"╚══════════════════════════════════════════╝"
        ))

        tops = result.get("top_signals", [])
        if tops:
            self.stdout.write("\n🏆 Top Signals:\n")
            self.stdout.write(f"  {'หุ้น':<10} {'สัญญาณ':<16} {'ทิศทาง':<8} {'คะแนน':>6} {'Stop Loss':>12} {'Risk%':>6}")
            self.stdout.write("  " + "─"*65)
            for sig in tops[:15]:
                de  = DIRECTION_EMOJI.get(sig.get("direction",""), "⬜")
                se  = SIGNAL_EMOJI.get(sig.get("signal_type",""), "⬜")
                sym = sig.get("symbol", str(sig.get("symbol_id","")))
                sl  = f"{sig['stop_loss']:.2f}" if sig.get("stop_loss") else "—"
                rp  = f"{sig['risk_pct']:.1f}%" if sig.get("risk_pct") else "—"
                self.stdout.write(
                    f"  {de}{se} {sym:<9} {sig.get('signal_type',''):<16} "
                    f"{sig.get('direction',''):<8} {sig.get('score',0):>6.0f} "
                    f"{sl:>12} {rp:>6}"
                )

    # ── Single symbol ───────────────────────────────────────────────────────
    def _run_single(self, sym_code, mode):
        try:
            sym = Symbol.objects.get(symbol=sym_code)
        except Symbol.DoesNotExist:
            raise CommandError(f"ไม่พบหุ้น '{sym_code}'")

        if mode in ("all","indicators"):
            from radar.indicator_engine import run_indicator_engine
            r = run_indicator_engine(sym)
            self.stdout.write(self.style.SUCCESS(
                f"📊 {sym_code} Indicator: {r['bars']} bars, saved {r['saved']} rows"
            ))

        if mode in ("all","signals"):
            from radar.signal_engine import run_signal_engine
            r = run_signal_engine(sym)
            if r:
                self.stdout.write(self.style.SUCCESS(
                    f"🔔 {sym_code} | {r['signal_type']} | {r['direction']} | "
                    f"score={r['score']:.1f} | SL={r.get('stop_loss') or '—'} | "
                    f"Risk={r.get('risk_pct') or '—'}% | ADX={r.get('adx') or '—'}"
                ))
                if r.get("reasons"):
                    for reason in r["reasons"]:
                        self.stdout.write(f"   → {reason}")
            else:
                self.stdout.write("⬜ ไม่มีสัญญาณ")

    # ── Celery ──────────────────────────────────────────────────────────────
    def _run_celery(self, mode, exchange):
        from radar.scanner_engine import run_full_scan_task
        run_ind = mode in ("all","indicators")
        task    = run_full_scan_task.delay(exchange=exchange, run_indicators=run_ind)
        self.stdout.write(self.style.SUCCESS(
            f"✅ ส่ง Celery task แล้ว\n   Task ID: {task.id}"
        ))

    # ── Summary ─────────────────────────────────────────────────────────────
    def _warmup_cache(self, exchange):
        """Warm up Redis cache หลัง run_engine เสร็จ"""
        try:
            from radar.indicator_cache import warm_up_cache, indicator_cache
            if not indicator_cache._is_available():
                self.stdout.write("   ⚠️  Redis ไม่พร้อม — ข้าม cache warm-up")
                return
            self.stdout.write("   🔥 Warming up Redis cache...")
            result = warm_up_cache(exchange)
            self.stdout.write(self.style.SUCCESS(
                f"   ✅ Cache warm-up: {result['warmed']} symbols | {result['elapsed_sec']:.2f}s"
            ))
        except Exception as e:
            self.stdout.write(f"   ⚠️  Cache warm-up ล้มเหลว: {e}")

    def _print_summary(self, elapsed, total, mode, ind_ok, ind_err, sig_ok, sig_err, sig_count):
        self.stdout.write(self.style.SUCCESS(
            f"\n╔══════════════════════════════════════════╗\n"
            f"║  ✅ สรุปผล                                ║\n"
            f"╠══════════════════════════════════════════╣\n"
            f"║  ⏱️  เวลา:         {elapsed:>8.2f} วินาที         ║\n"
            f"║  ⚡ เฉลี่ย/หุ้น:   {elapsed/max(total,1)*1000:>8.1f} ms              ║\n"
        ))
        if mode in ("all","indicators"):
            self.stdout.write(f"║  📊 Indicator ✅: {ind_ok:>6}  ❌: {ind_err:<6}         ║\n")
        if mode in ("all","signals"):
            self.stdout.write(
                f"║  🔔 Signal ✅:   {sig_ok:>6}  ❌: {sig_err:<6}         ║\n"
                f"║  📌 สัญญาณ:      {sig_count:>6} รายการ              ║\n"
            )
        self.stdout.write("╚══════════════════════════════════════════╝\n")
