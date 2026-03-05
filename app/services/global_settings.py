"""
Global system settings persisted to app/data/global_settings.json.
"""

import json
from pathlib import Path
from threading import Lock

SETTINGS_PATH = Path(__file__).resolve().parents[1] / "data" / "global_settings.json"
_VALID_END_EFFECTORS = {"gripper", "pump"}
_DEFAULT_SETTINGS = {"end_effector_type": "gripper"}

_settings_lock = Lock()


def _ensure_settings_file() -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.write_text(json.dumps(_DEFAULT_SETTINGS, indent=2), encoding="utf-8")


def _normalize_settings(data: dict) -> dict:
    end_effector_type = str(data.get("end_effector_type", "gripper")).strip().lower()
    if end_effector_type not in _VALID_END_EFFECTORS:
        end_effector_type = "gripper"
    return {"end_effector_type": end_effector_type}


def _read_settings() -> dict:
    with _settings_lock:
        _ensure_settings_file()
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = dict(_DEFAULT_SETTINGS)

        normalized = _normalize_settings(data)
        if normalized != data:
            SETTINGS_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
        return normalized


def get_end_effector_type() -> str:
    return _read_settings()["end_effector_type"]


def set_end_effector_type(end_effector_type: str) -> str:
    normalized = _normalize_settings({"end_effector_type": end_effector_type})
    with _settings_lock:
        _ensure_settings_file()
        SETTINGS_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    return normalized["end_effector_type"]


def get_end_effector_status_text() -> str:
    end_effector_type = get_end_effector_type()
    if end_effector_type == "pump":
        return "PUMP: DEACTIVATED"
    return "GRIPPER: CLOSED"
