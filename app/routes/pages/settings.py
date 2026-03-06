"""
Settings page + API.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.routes.pages._shared import _render
from app.services.global_settings import get_end_effector_type, set_end_effector_type

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return _render(
        request,
        "settings",
        "pages/settings.html",
        selected_end_effector=get_end_effector_type(),
    )

class ModelDeploy(BaseModel):
    model: str


class ArmInit(BaseModel):
    port: str = ""


class EndEffectorPayload(BaseModel):
    end_effector_type: str = Field(pattern="^(gripper|pump)$")

@router.post("/api/settings/deploy-physical")
async def deploy_physical(payload: ModelDeploy):
    """Deploy a physical / robot AI model."""
    logger.info("[settings] Deploy Physical AI Model -> %s", payload.model)
    return {"status": "ok", "model": payload.model}


@router.post("/api/settings/deploy-cv")
async def deploy_cv(payload: ModelDeploy):
    """Deploy a computer vision model (hot-swap YOLO)."""
    logger.info("[settings] Deploy CV Model -> %s", payload.model)
    return {"status": "ok", "model": payload.model}


@router.post("/api/settings/initialize-arm")
async def initialize_arm(payload: ArmInit):
    """Initialize the robotic arm connection."""
    logger.info("[settings] Initialize Arm - port:%s", payload.port or "auto")
    return {"status": "initialized", "port": payload.port}


@router.post("/api/settings/init")
async def initialize_arm_basic():
    """Initialize the robotic arm from the main Initialize Arm button."""
    logger.info("[settings] > INITIALIZING ARM to safe zero position")
    return {"status": "initialized"}


@router.get("/api/settings/end-effector")
async def get_end_effector_setting():
    return {"end_effector_type": get_end_effector_type()}


@router.post("/api/settings/end-effector")
async def set_end_effector_setting(payload: EndEffectorPayload):
    value = set_end_effector_type(payload.end_effector_type)
    logger.info("[settings] End effector set -> %s", value)
    return {"status": "ok", "end_effector_type": value}
