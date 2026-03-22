from django.apps import AppConfig
import os


class RadarConfig(AppConfig):
    name = "radar"

    def ready(self):
        # ป้องกัน double-run ใน dev (runserver reloader)
        if os.environ.get("RUN_MAIN") == "true":
            return

        # Price poller (real-time)
        try:
            from radar.price_poller import start_poller
            start_poller(interval=60)
        except Exception:
            pass

        # Scheduler — รันใน process เดียวกับ web server (ไม่ต้องการ worker แยก)
        if os.environ.get("RUN_SCHEDULER") == "true":
            try:
                from radar.scheduler import start_scheduler
                start_scheduler()
            except Exception:
                pass
