from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import webrtc
from app.routes.pages import all_routers as page_routers
from app.routes.webrtc import close_all_connections
from app.services.camera import start_camera, stop_camera
from app.services.detector import start_detector, stop_detector
from app.services.ros2_publisher import start_ros2_publisher, stop_ros2_publisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_camera()
    start_detector()
    start_ros2_publisher()
    yield
    stop_ros2_publisher()
    stop_detector()
    await close_all_connections()
    stop_camera()


app = FastAPI(title="MyCobot C2", lifespan=lifespan)

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
