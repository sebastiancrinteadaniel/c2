from contextlib import asynccontextmanager
import socket

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.server import get_server_settings
from app.routes import webrtc
from app.routes.pages import all_routers as page_routers
from app.routes.webrtc import close_all_connections
from app.services.camera import start_camera, stop_camera
from app.services.detector import start_detector, stop_detector
from app.services.ros2_publisher import start_ros2_publisher, stop_ros2_publisher
from app.services.system_metrics import get_system_metrics


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

    print("\n" + "=" * 56)
    print("[server] Access URLs")
    print(f"[server] Local:   http://127.0.0.1:{cfg.port}")
    if cfg.host == "0.0.0.0":
        print(f"[server] Network: http://{local_ip}:{cfg.port}")
        print("[server] Open the Network URL from another computer on this LAN")
    else:
        print(f"[server] Bound host: {cfg.host}")
    print("=" * 56 + "\n")


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

@app.post("/api/emergency-stop")
async def global_emergency_stop():
    """Trigger a system-wide emergency halt."""
    print("\n" + "="*50)
    print("[!] SYSTEM ALERT: GLOBAL EMERGENCY STOP TRIGGERED [!]")
    print("="*50 + "\n")
    #  TODO: send immediate halt instruction to robot controller 
    return {"status": "halted"}

app.mount("/static", StaticFiles(directory="static"), name="static")

for router in page_routers:
    app.include_router(router)
app.include_router(webrtc.router)
