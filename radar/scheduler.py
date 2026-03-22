"""
scheduler.py — In-process scheduler (รันใน thread ของ web server)
ใช้แทน worker process เพื่อประหยัดค่า Render
"""
import threading
import logging
import time
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
BKK = pytz.timezone("Asia/Bangkok")
_stop = threading.Event()


def _now_bkk():
    return datetime.now(BKK)


def _run_task(name: str, fn):
    try:
        logger.info("Scheduler: running %s", name)
        fn()
    except Exception as e:
        logger.error("Scheduler task %s error: %s", name, e)


def _scheduler_loop():
    logger.info("In-process scheduler started")
    last_run: dict = {}

    # Task definitions: (hour, minute) → (name, function)
    TASKS = [
        ((8,  0),  "fetch_news"),
        ((10, 0),  "fetch_news"),
        ((12, 0),  "fetch_news"),
        ((15, 0),  "fetch_news"),
        ((18, 0),  "load_set_prices"),
        ((18, 30), "fetch_news"),
        ((18, 30), "load_us_prices"),
        ((22, 0),  "load_set_prices"),
        ((22, 30), "fetch_news"),
        ((22, 30), "load_us_prices"),
        ((23, 0),  "compute_indicators"),
        ((23, 30), "run_signals"),
    ]

    while not _stop.is_set():
        now = _now_bkk()
        slot = (now.hour, now.minute)

        for (h, m), task_name in TASKS:
            if slot == (h, m):
                key = f"{task_name}-{now.date()}-{h:02d}{m:02d}"
                if key not in last_run:
                    last_run[key] = True
                    fn = _get_task_fn(task_name)
                    if fn:
                        t = threading.Thread(target=_run_task, args=(task_name, fn), daemon=True)
                        t.start()

        _stop.wait(30)  # ตรวจทุก 30 วินาที

    logger.info("Scheduler stopped")


def _get_task_fn(name: str):
    try:
        import django
        from django.core.management import call_command

        fns = {
            "fetch_news":        lambda: call_command("fetch_news"),
            "load_set_prices":   lambda: call_command("load_prices", "--exchange=SET", "--days=5"),
            "load_us_prices":    lambda: call_command("load_prices", "--exchange=US", "--days=5"),
            "compute_indicators":lambda: call_command("run_engine", "--indicators-only"),
            "run_signals":       lambda: call_command("run_engine", "--signals-only"),
        }
        return fns.get(name)
    except Exception:
        return None


def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, name="InProcessScheduler", daemon=True)
    t.start()
    return t


def stop_scheduler():
    _stop.set()
