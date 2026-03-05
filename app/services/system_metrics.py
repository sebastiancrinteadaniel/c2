"""
System metrics helpers shared by HTTP endpoints and WebRTC DataChannel push.
"""

import subprocess
import time

try:
    import psutil
except ImportError:
    psutil = None

_APP_STARTED_AT = time.time()
_LAST_GPU_SAMPLE_AT = 0.0
_LAST_GPU_VALUE: float | None = None


def _get_gpu_usage_percent() -> float | None:
    global _LAST_GPU_SAMPLE_AT, _LAST_GPU_VALUE

    now = time.time()
    if now - _LAST_GPU_SAMPLE_AT < 2.0:
        return _LAST_GPU_VALUE

    _LAST_GPU_SAMPLE_AT = now
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=0.8,
        )
        first_line = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        _LAST_GPU_VALUE = float(first_line) if first_line else None
    except Exception:
        _LAST_GPU_VALUE = None

    return _LAST_GPU_VALUE


def get_system_metrics() -> dict:
    uptime_seconds = int(max(0, time.time() - _APP_STARTED_AT))

    if psutil is None:
        return {
            "cpu_percent": None,
            "ram_percent": None,
            "gpu_percent": _get_gpu_usage_percent(),
            "uptime_seconds": uptime_seconds,
        }

    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "ram_percent": psutil.virtual_memory().percent,
        "gpu_percent": _get_gpu_usage_percent(),
        "uptime_seconds": uptime_seconds,
    }
