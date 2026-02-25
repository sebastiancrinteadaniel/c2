"""
Settings page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render

router = APIRouter()


# ── Page ──────────────────────────────────────────────────────────────────

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return _render(request, "settings", "pages/settings.html")


# ── Models ────────────────────────────────────────────────────────────────

class ModelDeploy(BaseModel):
    model: str

class ArmInit(BaseModel):
    port: str = ""


# ── API ───────────────────────────────────────────────────────────────────

@router.post("/api/settings/deploy-physical")
async def deploy_physical(payload: ModelDeploy):
    """Deploy a physical / robot AI model."""
    print(f"\n[settings] Deploy Physical AI Model \u2192 {payload.model}")
    # TODO: load model into robot controller
    return {"status": "ok", "model": payload.model}


@router.post("/api/settings/deploy-cv")
async def deploy_cv(payload: ModelDeploy):
    """Deploy a computer vision model (hot-swap YOLO)."""
    print(f"\n[settings] Deploy CV Model \u2192 {payload.model}")
    # TODO: hot-swap model in DetectorService
    return {"status": "ok", "model": payload.model}


@router.post("/api/settings/initialize-arm")
async def initialize_arm(payload: ArmInit):
    """Initialize the robotic arm connection."""
    print(f"\n[settings] Initialize Arm \u2014 port:{payload.port or 'auto'}")
    # TODO: connect to MyCobot via pymycobot
    return {"status": "initialized", "port": payload.port}
