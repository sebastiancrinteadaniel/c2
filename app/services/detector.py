from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import torch

from app.config.detector import DetectorSettings, get_detector_settings
from ultralytics import YOLO
from app.services.camera import set_detection_provider
from app.services.camera import get_camera_track

Detection = dict
logger = logging.getLogger(__name__)


class DetectorService:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.latest_detections: list[Detection] = []
        self._model = None
        self._cfg: Optional[DetectorSettings] = None
        self._device: Optional[str] = None

    def start(self) -> None:
        cfg = get_detector_settings()
        self._cfg = cfg

        if not cfg.detector_enabled:
            logger.info("[detector] Disabled via config - skipping model load")
            return

        self._running = True
        self._thread = threading.Thread(target=self._load_and_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self.latest_detections = []
        logger.info("[detector] Stopped")


    def _load_and_run(self) -> None:
        cfg = self._cfg

        if cfg.device:
            self._device = cfg.device
        elif torch.cuda.is_available():
            self._device = "cuda:0"
        else:
            self._device = "cpu"

        if self._device.startswith("cuda"):
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.set_float32_matmul_precision("high")

        try:
            self._model = YOLO(cfg.model_path)
            self._model.to(self._device)
            logger.info(
                "[detector] YOLOv8 ready - model:%s conf:%s device:%s half:%s",
                cfg.model_path,
                cfg.confidence,
                self._device,
                cfg.infer_half,
            )
        except Exception:
            logger.exception("[detector] Failed to load model")
            self._running = False
            return

        set_detection_provider(lambda: self.latest_detections)

        self._inference_loop()

    def _inference_loop(self) -> None:
        cfg = self._cfg
        skip = max(0, cfg.infer_skip_frames)
        device = self._device

        last_frame_id = -1
        skip_counter  = 0

        while self._running:
            camera = get_camera_track()
            frame_id = camera.infer_frame_id
            frame    = camera.latest_bgr_infer

            if frame is None or frame_id == last_frame_id:
                time.sleep(0.005)
                continue

            if skip > 0:
                skip_counter += 1
                if skip_counter < skip:
                    last_frame_id = frame_id
                    time.sleep(0.001)
                    continue
                skip_counter = 0

            last_frame_id = frame_id

            frame = frame.copy()
            h, w = frame.shape[:2]

            try:
                results = self._model(
                    frame,
                    conf=cfg.confidence,
                    iou=cfg.iou,
                    device=device,
                    half=cfg.infer_half,
                    verbose=False,
                )
            except Exception:
                logger.exception("[detector] Inference error")
                time.sleep(0.1)
                continue

            detections: list[Detection] = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                names = result.names
                for box in boxes:
                    cls_id = int(box.cls[0])
                    xyxy   = box.xyxy[0].tolist()
                    detections.append({
                        "label":      names[cls_id],
                        "confidence": float(box.conf[0]),
                        "x1": xyxy[0] / w,
                        "y1": xyxy[1] / h,
                        "x2": xyxy[2] / w,
                        "y2": xyxy[3] / h,
                    })

            self.latest_detections = detections


_detector: Optional[DetectorService] = None


def get_detector() -> DetectorService:
    global _detector
    if _detector is None:
        _detector = DetectorService()
    return _detector


def start_detector() -> None:
    get_detector().start()


def stop_detector() -> None:
    global _detector
    if _detector is not None:
        _detector.stop()
        _detector = None
