import sys
import os

# Ensure the root directory is in sys.path so 'app.*' imports work when running this file directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from contextlib import asynccontextmanager
import logging
import socket

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.logging import configure_logging
from app.config.server import get_server_settings
from app.routes.pages import all_routers as page_routers
from app.routes.webrtc import close_all_peer_connections, router as webrtc_router
from app.services.ros2_publisher import (
    get_ros2_status,
    start_ros2_publisher,
    stop_ros2_publisher,
)
from app.services.system_metrics import get_system_metrics
from app.services.yolo_processor import preload_shared_yolo_processor


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    preload_shared_yolo_processor()
    start_ros2_publisher()
    yield
    await close_all_peer_connections()
    stop_ros2_publisher()


app = FastAPI(title="MyCobot C2", lifespan=lifespan)


@app.get("/api/system-metrics")
async def system_metrics():
    return get_system_metrics()


@app.get("/api/health")
async def health():
    ros2 = get_ros2_status()
    return {
        "status": "ok",
        "services": {
            "ros2": ros2,
        },
    }


@app.get("/api/ready")
async def ready():
    ros2 = get_ros2_status()

    ros2_ok = ros2["ready"] or not ros2["available"]
    is_ready = ros2_ok

    return {
        "ready": is_ready,
        "checks": {
            "ros2": ros2_ok,
        },
        "services": {
            "ros2": ros2,
        },
    }


@app.post("/api/emergency-stop")
async def global_emergency_stop():
    """Trigger a system-wide emergency halt."""
    logger.warning("%s", "=" * 50)
    logger.warning("[!] SYSTEM ALERT: GLOBAL EMERGENCY STOP TRIGGERED [!]")
    logger.warning("%s", "=" * 50)
    return {"status": "halted"}


app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/mockups", StaticFiles(directory="mockups"), name="mockups")

for router in page_routers:
    app.include_router(router)

app.include_router(webrtc_router)


if __name__ == "__main__":
    import uvicorn
    import socket

    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(("10.255.255.255", 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = "127.0.0.1"
        finally:
            s.close()
        return IP

    local_ip = get_ip()
    logger.info("\n" + "=" * 50)
    logger.info("🚀 Dashboard is running!")
    logger.info("👉 Local:   http://localhost:8000")
    logger.info(f"👉 Network: http://{local_ip}:8000")
    logger.info("=" * 50 + "\n")

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
