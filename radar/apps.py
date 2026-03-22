from django.apps import AppConfig


class RadarConfig(AppConfig):
    name = "radar"

    def ready(self):
        import os
        # เฉพาะ main process (ไม่รัน reloader process ซ้ำ)
        if os.environ.get("RUN_MAIN") != "true" and os.environ.get("DAPHNE") != "false":
            try:
                from radar.price_poller import start_poller
                start_poller(interval=60)
            except Exception:
                pass
