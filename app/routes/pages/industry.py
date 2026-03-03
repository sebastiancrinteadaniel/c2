"""
Industry 5.0 - sorting page + API.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render
from app.services.ros2_publisher import publish_command

# ---------------------------------------------------------------------------
# Hardcoded FSM command (from context.md) — swap for dynamic payload later
# ---------------------------------------------------------------------------
HARDCODED_FSM_COMMAND = {
    "end_effector_type": "gripper",
    "loop": False,
    "states": [
        {
            "type": "SetPositionState",
            "joint_angles": [0.0, 0.0, 1.8, 0.0, 0.0, 0.0],
        },
        {
            "type": "ReachTargetState",
            "point_goal": [0.0, -0.20, 0.04, 0.7071, 0.7071, 0.0, 0.0],
        },
        {
            "type": "EndEffectorState",
            "action": "close",
            "duration": 1.0,
        },
        {
            "type": "ReachTargetState",
            "point_goal": [0.15, -0.13, 0.08, 0.7071, 0.7071, 0.0, 0.0],
        },
        {
            "type": "EndEffectorState",
            "action": "open",
            "duration": 1.0,
        },
    ],
}

router = APIRouter()


#  Page 

@router.get("/", response_class=HTMLResponse)
async def industry_page(request: Request):
    return _render(request, "industry", "pages/industry.html")


#  Models 

class MappingEntry(BaseModel):
    part: str
    bin: int

class MappingPayload(BaseModel):
    mapping: list[MappingEntry]


#  API 

@router.post("/api/industry/mapping")
async def industry_mapping(payload: MappingPayload):
    """Called whenever the user changes a part->bin row."""
    print("\n[industry] Mapping updated:")
    for e in payload.mapping:
        print(f"  part={e.part!r:20s}  bin={e.bin}")
    return {"status": "ok"}


@router.post("/api/industry/start")
async def industry_start(payload: MappingPayload):
    """Called when the user presses Start Task."""
    print("\n" + "="*40)
    print("[industry] > START TASK TRIGGERED")
    print("="*40)
    if not payload.mapping:
        print("  (Warning: No mappings configured or selected!)")
    else:
        print("  Current mapping setup:")
        for e in payload.mapping:
            print(f"    - part={e.part!r:20s}  bin={e.bin}")
    print("="*40 + "\n")
    publish_command(HARDCODED_FSM_COMMAND)
    print("[industry] FSM command published.")
    return {"status": "started"}
