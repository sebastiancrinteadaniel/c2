"""
Interactive mode page + API.
"""

from typing import List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render
from app.services.fsm_command import build_hardcoded_fsm_command
from app.services.ros2_publisher import publish_command

router = APIRouter()


#  Page 

@router.get("/interactive", response_class=HTMLResponse)
async def interactive_page(request: Request):
    return _render(request, "interactive", "pages/interactive.html")


#  Models 

class DetectionToggle(BaseModel):
    enabled: bool

class TargetsPayload(BaseModel):
    targets: List[str]

class StartPayload(BaseModel):
    targets: List[str]
    detection: bool


#  API 

@router.post("/api/interactive/detection")
async def interactive_detection(payload: DetectionToggle):
    """Toggle hand-gesture detection on/off."""
    state = "ENABLED" if payload.enabled else "DISABLED"
    print(f"\n[interactive] Detection -> {state}")
    # TODO: start/stop gesture detection service
    return {"status": "ok", "enabled": payload.enabled}


@router.post("/api/interactive/targets")
async def interactive_targets(payload: TargetsPayload):
    """Sync the ordered target priority list."""
    print("\n[interactive] Target priorities updated:")
    for i, name in enumerate(payload.targets, 1):
        print(f"  priority {i}: {name}")
    # TODO: push updated priorities to robot controller
    return {"status": "ok", "count": len(payload.targets)}


@router.post("/api/interactive/start")
async def interactive_start(payload: StartPayload):
    """Start the interactive task with current configuration."""
    print("\n" + "="*40)
    print("[interactive] > START TASK TRIGGERED")
    print("="*40)
    print(f"  Detection Active: {payload.detection}")
    print(f"  Targets Order:    {payload.targets}")
    print("="*40 + "\n")
    publish_command(build_hardcoded_fsm_command())
    print("[interactive] FSM command published.")
    return {"status": "started"}
