"""YOLOv8 object detection utilities for camera streams."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


logger = logging.getLogger(__name__)

_IMGSZ = 640
_CONF = 0.45

try:
    from ultralytics import YOLO
except Exception:  # pragma: no cover - optional dependency
    YOLO = None


def _default_model_path() -> Path:
    # Project root is two levels up from app/services/.
    root = Path(__file__).resolve().parents[2]
    return root / "models" / "yolov8n.pt"


class YOLOProcessor:
    """Run YOLO inference and return annotated frames + normalized detections."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        imgsz: int = _IMGSZ,
        conf: float = _CONF,
    ) -> None:
        self._imgsz = imgsz
        self._conf = conf
        self._model = None
        self._load_error: str | None = None

        candidate = Path(model_path) if model_path else _default_model_path()
        if YOLO is None:
            self._load_error = "ultralytics package is not installed"
            logger.warning("[yolo] %s; detection overlay disabled", self._load_error)
            return

        if not candidate.exists():
            self._load_error = f"model file not found at {candidate}"
            logger.warning("[yolo] %s; detection overlay disabled", self._load_error)
            return

        try:
            self._model = YOLO(str(candidate))
            logger.info("[yolo] loaded model from %s", candidate)
        except Exception as exc:  # pragma: no cover - model runtime issue
            self._load_error = str(exc)
            logger.exception("[yolo] failed to load model: %s", exc)

    @property
    def ready(self) -> bool:
        return self._model is not None

    @property
    def status_message(self) -> str:
        if self._model is not None:
            return "ready"
        return self._load_error or "model unavailable"

    def warmup(self) -> None:
        """Run a dummy inference once to reduce initial latency spikes."""
        if self._model is None:
            return

        dummy = np.zeros((self._imgsz, self._imgsz, 3), dtype=np.uint8)
        self._model(dummy, imgsz=self._imgsz, conf=self._conf, verbose=False)

    def process(self, frame: np.ndarray) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        if self._model is None:
            return frame, []

        try:
            results = self._model(frame, imgsz=self._imgsz, conf=self._conf, verbose=False)
            result = results[0]
            annotated = result.plot()
            detections: List[Dict[str, Any]] = []

            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    {
                        "class": self._model.names[cls_id],
                        "conf": round(conf, 3),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    }
                )

            return annotated, detections
        except Exception as exc:  # pragma: no cover - runtime inference issue
            logger.exception("[yolo] inference failure: %s", exc)
            return frame, []
