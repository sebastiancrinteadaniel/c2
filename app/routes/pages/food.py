"""
Food QA - quality assurance page + API.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from pydantic import BaseModel, Field

from app.routes.pages._shared import _render
from app.services.fsm_command import build_hardcoded_fsm_command
from app.services.ros2_publisher import publish_command

router = APIRouter()
logger = logging.getLogger(__name__)

class MappingEntry(BaseModel):
    product: str
    quantity: int = Field(ge=0, le=99)

class MappingPayload(BaseModel):
    mapping: list[MappingEntry]

@router.get("/food", response_class=HTMLResponse)
async def food_page(request: Request):
    return _render(request, "food", "pages/food.html")

@router.post("/api/food/halt")
async def food_halt():
    """Called when the user presses Halt Production Cycle."""
    logger.info("[food] > HALT PRODUCTION CYCLE triggered - TODO: stop conveyor / robot")
    return {"status": "halted"}

@router.post("/api/food/start")
async def food_start(payload: MappingPayload):
    """Called when the user presses Start Task."""
    logger.info("%s", "=" * 40)
    logger.info("[food] > START TASK TRIGGERED")
    logger.info("%s", "=" * 40)
    if not payload.mapping:
        logger.warning("[food] No products mapped")
    else:
        logger.info("  Current product mapping:")
        for e in payload.mapping:
            logger.info("    - product=%r  quantity=%s", e.product, e.quantity)
    logger.info("%s", "=" * 40)
    publish_result = publish_command(build_hardcoded_fsm_command())
    if publish_result["published"]:
        logger.info("[food] FSM command published.")
        return {"status": "started", "command": publish_result}
    logger.warning("[food] FSM command not published: %s", publish_result["reason"])
    return {"status": "error", "command": publish_result}
