"""
Healthcare - RX verification page + API.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.routes.pages._shared import _render
from app.services.fsm_command import build_hardcoded_fsm_command
from app.services.ros2_publisher import publish_command

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/healthcare", response_class=HTMLResponse)
async def healthcare_page(request: Request):
    return _render(request, "healthcare", "pages/healthcare.html")


class HealthcareStart(BaseModel):
    injection_length: int

@router.post("/api/healthcare/inspect")
async def healthcare_inspect():
    """Called when the user presses Inspect on an RX document."""
    logger.info("[healthcare] > INSPECT triggered - TODO: run OCR / text detection on RX doc")
    return {"status": "inspect_started"}

@router.post("/api/healthcare/start")
async def healthcare_start(payload: HealthcareStart):
    """Called when the user presses Start Task."""
    logger.info("%s", "=" * 40)
    logger.info("[healthcare] > START TASK TRIGGERED")
    logger.info("%s", "=" * 40)
    logger.info("  Injection Length: %smm", payload.injection_length)
    logger.info("%s", "=" * 40)
    publish_result = publish_command(build_hardcoded_fsm_command())
    if publish_result["published"]:
        logger.info("[healthcare] FSM command published.")
        return {"status": "started", "command": publish_result}
    logger.warning("[healthcare] FSM command not published: %s", publish_result["reason"])
    return {"status": "error", "command": publish_result}
