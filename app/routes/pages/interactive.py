"""
Interactive mode page + API.
"""

import logging

from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render
from app.services.fsm_command import build_hardcoded_fsm_command
from app.services.ros2_publisher import publish_command

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/interactive", response_class=HTMLResponse)
async def interactive_page(request: Request):
    return _render(request, "interactive", "pages/interactive.html")

class DetectionToggle(BaseModel):
    enabled: bool

class TargetsPayload(BaseModel):
    targets: List[str]

class StartPayload(BaseModel):
    targets: List[str]
    detection: bool

@router.post("/api/interactive/detection")
async def interactive_detection(payload: DetectionToggle):
    """Toggle hand-gesture detection on/off."""
    state = "ENABLED" if payload.enabled else "DISABLED"
    logger.info("[interactive] Detection -> %s", state)
    return {"status": "ok", "enabled": payload.enabled}


@router.post("/api/interactive/targets")
async def interactive_targets(payload: TargetsPayload):
    """Sync the ordered target priority list."""
    logger.info("[interactive] Target priorities updated:")
    for i, name in enumerate(payload.targets, 1):
        logger.info("  priority %s: %s", i, name)
    return {"status": "ok", "count": len(payload.targets)}


@router.post("/api/interactive/start")
async def interactive_start(payload: StartPayload):
    """Start the interactive task with current configuration."""
    logger.info("%s", "=" * 40)
    logger.info("[interactive] > START TASK TRIGGERED")
    logger.info("%s", "=" * 40)
    logger.info("  Detection Active: %s", payload.detection)
    logger.info("  Targets Order:    %s", payload.targets)
    logger.info("%s", "=" * 40)
    publish_command(build_hardcoded_fsm_command())
    logger.info("[interactive] FSM command published.")
    return {"status": "started"}
