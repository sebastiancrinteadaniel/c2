"""
Settings page + API.
"""

import logging
from pathlib import Path

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


class CalibrationStartPayload(BaseModel):
    mode: str = "charuco_6d_pose"


def _get_mock_calibration_images() -> list[Path]:
    project_root = Path(__file__).resolve().parents[3]
    calibration_dir = project_root / "mockups" / "calibration"
    if not calibration_dir.exists():
        return []

    candidates = sorted(
        [
            *calibration_dir.glob("*.png"),
            *calibration_dir.glob("*.jpg"),
            *calibration_dir.glob("*.jpeg"),
            *calibration_dir.glob("*.webp"),
        ]
    )
    return [path for path in candidates if path.is_file()]

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


@router.post("/api/settings/calibration/start")
async def start_camera_calibration(payload: CalibrationStartPayload):
    logger.info(
        "[settings] Camera calibration start requested -> mode:%s (attach ChArUco board)",
        payload.mode,
    )

    source_images = _get_mock_calibration_images()
    images = []
    for i, image_path in enumerate(source_images, start=1):
        corners = 48 + ((i * 7) % 28)
        images.append(
            {
                "id": f"calib-{i:02d}",
                "frame_index": i,
                "preview_src": f"/mockups/calibration/{image_path.name}",
                "charuco_corners": corners,
                "charuco_ids": max(corners - 6, 0),
                "reprojection_error_px": round(0.18 + (i * 0.047), 3),
                "pose_quality": "good" if i % 3 != 0 else "fair",
                "timestamp": f"2026-03-18T14:{20 + i:02d}:11Z",
            }
        )

    if not images:
        logger.warning("[settings] No mock calibration images found under mockups/calibration")

    return {
        "status": "ok",
        "mode": payload.mode,
        "calibration_active": True,
        "can_connect_stream": False,
        "summary": {
            "captured_images": len(images),
            "usable_images": sum(1 for item in images if item["pose_quality"] == "good"),
            "avg_reprojection_error_px": round(
                sum(item["reprojection_error_px"] for item in images) / len(images),
                3,
            ),
        },
        "images": images,
    }
