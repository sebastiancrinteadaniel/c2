from contextlib import asynccontextmanager
import logging
import socket

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.logging import configure_logging
from app.config.server import get_server_settings
from app.routes import webrtc
from app.routes.pages import all_routers as page_routers
from app.routes.webrtc import close_all_connections
from app.services.camera import get_camera_status, start_camera, stop_camera
from app.services.detector import get_detector_status, start_detector, stop_detector
from app.services.ros2_publisher import get_ros2_status, start_ros2_publisher, stop_ros2_publisher
from app.services.system_metrics import get_system_metrics


configure_logging()
logger = logging.getLogger(__name__)


def _get_local_ipv4() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def _print_access_urls() -> None:
    cfg = get_server_settings()
    local_ip = _get_local_ipv4()

    logger.info("%s", "=" * 56)
    logger.info("[server] Access URLs")
    logger.info("[server] Local:   http://127.0.0.1:%s", cfg.port)
    if cfg.host == "0.0.0.0":
        logger.info("[server] Network: http://%s:%s", local_ip, cfg.port)
        logger.info("[server] Open the Network URL from another computer on this LAN")
    else:
        logger.info("[server] Bound host: %s", cfg.host)
    logger.info("%s", "=" * 56)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _print_access_urls()
    start_camera()
    start_detector()
    start_ros2_publisher()
    yield
    stop_ros2_publisher()
    stop_detector()
    await close_all_connections()
    stop_camera()


app = FastAPI(title="MyCobot C2", lifespan=lifespan)


@app.get("/api/system-metrics")
async def system_metrics():
    return get_system_metrics()


@app.get("/api/health")
async def health():
    camera = get_camera_status()
    detector = get_detector_status()
    ros2 = get_ros2_status()
    return {
        "status": "ok",
        "services": {
            "camera": camera,
            "detector": detector,
            "ros2": ros2,
        },
    }


@app.get("/api/ready")
async def ready():
    camera = get_camera_status()
    detector = get_detector_status()
    ros2 = get_ros2_status()

    ros2_ok = ros2["ready"] or not ros2["available"]
    is_ready = camera["ready"] and detector["ready"] and ros2_ok

    return {
        "ready": is_ready,
        "checks": {
            "camera": camera["ready"],
            "detector": detector["ready"],
            "ros2": ros2_ok,
        },
        "services": {
            "camera": camera,
            "detector": detector,
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

for router in page_routers:
    app.include_router(router)
app.include_router(webrtc.router)
