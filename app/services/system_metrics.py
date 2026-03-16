"""
System metrics helpers shared by HTTP endpoints and WebRTC DataChannel push.
"""

import time

try:
    import psutil
except ImportError:
    psutil = None

_APP_STARTED_AT = time.time()


def get_system_metrics() -> dict:
    uptime_seconds = int(max(0, time.time() - _APP_STARTED_AT))

    if psutil is None:
        return {
            "cpu_percent": None,
            "ram_percent": None,
            "uptime_seconds": uptime_seconds,
        }

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent,
        "uptime_seconds": uptime_seconds,
    }
