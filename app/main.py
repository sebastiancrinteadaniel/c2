from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import pages, webrtc
from app.routes.webrtc import close_all_connections
from app.services.camera import start_camera, stop_camera
from app.services.detector import start_detector, stop_detector


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_camera()
    start_detector()
    yield
    stop_detector()
    await close_all_connections()
    stop_camera()


app = FastAPI(title="MyCobot C2", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(pages.router)
app.include_router(webrtc.router)
