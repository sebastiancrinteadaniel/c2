"""
Industry 5.0 - sorting page + API.
"""

import logging
import json
from pathlib import Path
from threading import Lock

from fastapi import APIRouter, Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.routes.pages._shared import _render
from app.services.fsm_command import build_hardcoded_fsm_command
from app.services.ros2_publisher import publish_command

router = APIRouter()
logger = logging.getLogger(__name__)

PROFILES_PATH = Path(__file__).resolve().parents[2] / "data" / "industry_profiles.json"
_profiles_lock = Lock()
_applied_mapping_lock = Lock()
_applied_mapping: list[dict] = []

DEFAULT_PROFILES = {
    "profiles": [
        {
            "name": "Mixed Assembly",
            "mapping": [
                {"part": "Small gear", "quantity": 30},
                {"part": "Large gear", "quantity": 20},
                {"part": "U-Bracket", "quantity": 10},
                {"part": "Double Eye Link", "quantity": 15},
            ],
        },
        {
            "name": "Gears Only",
            "mapping": [
                {"part": "Small gear", "quantity": 25},
                {"part": "Large gear", "quantity": 25},
            ],
        },
        {
            "name": "Links & Brackets",
            "mapping": [
                {"part": "U-Bracket", "quantity": 40},
                {"part": "Double Eye Link", "quantity": 35},
            ],
        },
    ]
}


def _validate_profiles_payload(data: dict):
    profiles = data.get("profiles")
    if not isinstance(profiles, list):
        raise ValueError("Invalid profile store: 'profiles' must be a list")

    seen_names = set()
    for profile in profiles:
        name = profile.get("name")
        mapping = profile.get("mapping")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Invalid profile store: profile name must be a non-empty string")
        lowered_name = name.strip().casefold()
        if lowered_name in seen_names:
            raise ValueError("Invalid profile store: duplicate profile names found")
        seen_names.add(lowered_name)
        if not isinstance(mapping, list):
            raise ValueError("Invalid profile store: mapping must be a list")
        for entry in mapping:
            if not isinstance(entry, dict):
                raise ValueError("Invalid profile store: mapping entries must be objects")
            if not isinstance(entry.get("part"), str) or not entry["part"].strip():
                raise ValueError("Invalid profile store: mapping.part must be a non-empty string")
            if not isinstance(entry.get("quantity"), int):
                raise ValueError("Invalid profile store: mapping.quantity must be an integer")


def _normalize_profiles_payload(data: dict) -> tuple[dict, bool]:
    changed = False
    profiles = data.get("profiles") if isinstance(data, dict) else None
    if not isinstance(profiles, list):
        return data, changed

    for profile in profiles:
        mapping = profile.get("mapping") if isinstance(profile, dict) else None
        if not isinstance(mapping, list):
            continue

        for entry in mapping:
            if not isinstance(entry, dict):
                continue
            if "quantity" not in entry and "bin" in entry:
                entry["quantity"] = entry.pop("bin")
                changed = True

    return data, changed


def _ensure_profiles_file():
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PROFILES_PATH.exists():
        PROFILES_PATH.write_text(json.dumps(DEFAULT_PROFILES, indent=2), encoding="utf-8")


def _read_profiles() -> dict:
    with _profiles_lock:
        _ensure_profiles_file()
        try:
            data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise HTTPException(status_code=500, detail=f"Invalid profile JSON: {err}") from err

        data, changed = _normalize_profiles_payload(data)

        try:
            _validate_profiles_payload(data)
        except ValueError as err:
            raise HTTPException(status_code=500, detail=str(err)) from err

        if changed:
            _write_profiles(data)

        return data


def _write_profiles(data: dict):
    with _profiles_lock:
        _validate_profiles_payload(data)
        PROFILES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

@router.get("/", response_class=HTMLResponse)
async def industry_page(request: Request):
    _ensure_profiles_file()
    return _render(request, "industry", "pages/industry.html")

class MappingEntry(BaseModel):
    part: str = Field(min_length=1)
    quantity: int = Field(ge=0, le=99)

class MappingPayload(BaseModel):
    mapping: list[MappingEntry]


class ProfileRecord(BaseModel):
    name: str = Field(min_length=1)
    mapping: list[MappingEntry]


class ProfilesResponse(BaseModel):
    profiles: list[ProfileRecord]


class ProfileCreatePayload(BaseModel):
    name: str = Field(min_length=1)
    mapping: list[MappingEntry]


class ProfileUpdatePayload(BaseModel):
    name: str = Field(min_length=1)
    mapping: list[MappingEntry]


class ProfileDeletePayload(BaseModel):
    name: str = Field(min_length=1)

@router.post("/api/industry/mapping")
async def industry_mapping(payload: MappingPayload):
    """Called only when the user applies the global mapping."""
    with _applied_mapping_lock:
        _applied_mapping.clear()
        _applied_mapping.extend([entry.model_dump() for entry in payload.mapping])

    logger.info("[industry] Mapping updated:")
    for e in payload.mapping:
        logger.info("  part=%r  quantity=%s", e.part, e.quantity)
    return {"status": "ok"}


@router.post("/api/industry/start")
async def industry_start():
    """Called when the user presses Start Task."""
    with _applied_mapping_lock:
        current_mapping = list(_applied_mapping)

    if not current_mapping:
        raise HTTPException(status_code=400, detail="No applied mapping. Press 'Apply Global Mapping' first.")

    logger.info("%s", "=" * 40)
    logger.info("[industry] > START TASK TRIGGERED")
    logger.info("%s", "=" * 40)
    logger.info("  Applied mapping setup:")
    for entry in current_mapping:
        logger.info("    - part=%r  quantity=%s", entry["part"], entry["quantity"])
    logger.info("%s", "=" * 40)
    publish_result = publish_command(build_hardcoded_fsm_command())
    if publish_result["published"]:
        logger.info("[industry] FSM command published.")
        return {"status": "started", "command": publish_result}
    logger.warning("[industry] FSM command not published: %s", publish_result["reason"])
    return {"status": "error", "command": publish_result}


@router.get("/api/industry/profiles", response_model=ProfilesResponse)
async def list_industry_profiles():
    data = _read_profiles()
    return {"profiles": data["profiles"]}


@router.post("/api/industry/profiles")
async def create_industry_profile(payload: ProfileCreatePayload):
    profile_name = payload.name.strip()
    data = _read_profiles()

    existing_names = {p["name"].strip().casefold() for p in data["profiles"]}
    if profile_name.casefold() in existing_names:
        raise HTTPException(status_code=409, detail="Profile name already exists")

    data["profiles"].append({"name": profile_name, "mapping": [e.model_dump() for e in payload.mapping]})
    _write_profiles(data)
    return {"status": "created", "profile": {"name": profile_name, "mapping": payload.mapping}}


@router.post("/api/industry/profiles/update")
async def update_industry_profile(payload: ProfileUpdatePayload):
    profile_name = payload.name.strip()
    data = _read_profiles()

    for profile in data["profiles"]:
        if profile["name"].strip().casefold() == profile_name.casefold():
            profile["mapping"] = [e.model_dump() for e in payload.mapping]
            _write_profiles(data)
            return {"status": "updated", "profile": {"name": profile_name, "mapping": payload.mapping}}

    raise HTTPException(status_code=404, detail="Profile not found")


@router.post("/api/industry/profiles/delete")
async def delete_industry_profile(payload: ProfileDeletePayload):
    profile_name = payload.name.strip()
    data = _read_profiles()
    before = len(data["profiles"])

    data["profiles"] = [
        profile for profile in data["profiles"]
        if profile["name"].strip().casefold() != profile_name.casefold()
    ]

    if len(data["profiles"]) == before:
        raise HTTPException(status_code=404, detail="Profile not found")

    _write_profiles(data)
    return {"status": "deleted", "name": profile_name}
