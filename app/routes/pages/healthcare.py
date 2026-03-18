"""
Healthcare - RX verification page + API.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.routes.pages._shared import _render
from app.services.fsm_command import build_hardcoded_fsm_command
from app.services.healthcare_verification import get_healthcare_session
from app.services.ros2_publisher import publish_command

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/healthcare", response_class=HTMLResponse)
async def healthcare_page(request: Request):
    return _render(request, "healthcare", "pages/healthcare.html")


class HealthcareStart(BaseModel):
    injection_length: int


class HealthcareRxList(BaseModel):
    medicines: list[str] = Field(default_factory=list)

@router.post("/api/healthcare/inspect")
async def healthcare_inspect():
    """Backward-compatible alias that starts RX capture mode."""
    session = get_healthcare_session()
    snapshot = session.start_capture(reset=True)
    logger.info("[healthcare] RX capture started via inspect")
    return {"status": "capture_started", "healthcare": snapshot}


@router.post("/api/healthcare/start-rx-capture")
async def healthcare_start_rx_capture():
    """Start collecting RX candidates from live detections."""
    session = get_healthcare_session()
    snapshot = session.start_capture(reset=True)
    logger.info("[healthcare] RX capture mode enabled")
    return {"status": "capture_started", "healthcare": snapshot}


@router.post("/api/healthcare/start-rx-add")
async def healthcare_start_rx_add():
    """Start add-more capture mode without clearing current RX list."""
    session = get_healthcare_session()
    snapshot = session.start_capture(reset=False)
    logger.info("[healthcare] RX add-more mode enabled")
    return {"status": "capture_add_started", "healthcare": snapshot}


@router.post("/api/healthcare/add-captured-items")
async def healthcare_add_captured_items(payload: HealthcareRxList):
    """Append captured candidates (or provided items) to current RX list."""
    session = get_healthcare_session()
    snapshot = session.add_captured_items(payload.medicines)
    logger.info("[healthcare] appended captured items, RX list now %s", len(snapshot.get("rx_list", [])))
    return {"status": "captured_items_added", "healthcare": snapshot}


@router.post("/api/healthcare/confirm-rx-list")
async def healthcare_confirm_rx_list(payload: HealthcareRxList):
    """Confirm extracted RX medicine list before verification mode."""
    session = get_healthcare_session()
    if payload.medicines:
        snapshot = session.confirm_rx_list(payload.medicines)
    else:
        snapshot = session.finish_capture()
    logger.info("[healthcare] RX list confirmed with %s items", len(snapshot.get("rx_list", [])))
    return {"status": "rx_confirmed", "healthcare": snapshot}


@router.post("/api/healthcare/start-verification")
async def healthcare_start_verification():
    """Start verification against confirmed RX list."""
    session = get_healthcare_session()
    snapshot = session.start_verification()
    logger.info("[healthcare] verification started with %s items", snapshot.get("total", 0))
    return {"status": "verification_started", "healthcare": snapshot}


@router.post("/api/healthcare/stop-verification")
async def healthcare_stop_verification():
    """Stop healthcare verification and return idle."""
    session = get_healthcare_session()
    snapshot = session.stop_verification()
    logger.info("[healthcare] verification stopped")
    return {"status": "verification_stopped", "healthcare": snapshot}


@router.get("/api/healthcare/state")
async def healthcare_state():
    """Return current healthcare verification session state."""
    return {"healthcare": get_healthcare_session().snapshot()}

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
