from __future__ import annotations

import threading
import time
from typing import Optional

import torch

from app.config.detector import DetectorSettings, get_detector_settings
from ultralytics import YOLO
from app.services.camera import set_detection_provider
from app.services.camera import get_camera_track


# Detection dict shape:
#   { label: str, confidence: float, x1: float, y1: float, x2: float, y2: float }
#   coordinates normalised 0-1 relative to the INFER resolution frame.
Detection = dict


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
            print("[detector] Disabled via config - skipping model load")
            return

        self._running = True
        self._thread = threading.Thread(target=self._load_and_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self.latest_detections = []
        print("[detector] Stopped")


    def _load_and_run(self) -> None:
        cfg = self._cfg

        # Resolve inference device explicitly — never rely on Ultralytics auto-select
        # which can silently fall back to CPU even when CUDA is available.
        if cfg.device:
            self._device = cfg.device
        elif torch.cuda.is_available():
            self._device = "cuda:0"
        else:
            self._device = "cpu"

        # RTX 5000 series (Blackwell) and some other new GPUs hit
        # CUBLAS_STATUS_INVALID_VALUE with FP32 sgemm in torch 2.x.
        # TF32 routes those ops through tensor cores and avoids the bug.
        if self._device.startswith("cuda"):
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            torch.set_float32_matmul_precision("high")

        try:
            self._model = YOLO(cfg.model_path)
            self._model.to(self._device)
            # Ultralytics converts weights to FP16 lazily on the first inference
            # call, meaning the very first cublasSgemm (FP32) still fires and
            # crashes on Blackwell. Force the conversion now, upfront.
            if cfg.infer_half and self._device.startswith("cuda"):
                self._model.model.half()
            print(
                f"[detector] YOLOv8 ready - model:{cfg.model_path}  "
                f"conf:{cfg.confidence}  device:{self._device}  "
                f"half:{cfg.infer_half}"
            )
        except Exception as exc:
            print(f"[detector] Failed to load model: {exc}")
            self._running = False
            return

        # Register ourselves as the provider so camera.py draws our boxes
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

            #  Frame-skip logic 
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

            #  Copy frame so camera thread can overwrite safely 
            frame = frame.copy()
            h, w = frame.shape[:2]

            #  Run inference 
            try:
                results = self._model(
                    frame,
                    conf=cfg.confidence,
                    iou=cfg.iou,
                    device=device,
                    half=cfg.infer_half,
                    verbose=False,
                )
            except Exception as exc:
                print(f"[detector] Inference error: {exc}")
                time.sleep(0.1)
                continue

            #  Parse results -> normalised detections 
            detections: list[Detection] = []
            for result in results:
                boxes = result.boxes
                if boxes is None:
                    continue
                names = result.names
                for box in boxes:
                    cls_id = int(box.cls[0])
                    xyxy   = box.xyxy[0].tolist()   # pixel coords in infer res
                    detections.append({
                        "label":      names[cls_id],
                        "confidence": float(box.conf[0]),
                        "x1": xyxy[0] / w,
                        "y1": xyxy[1] / h,
                        "x2": xyxy[2] / w,
                        "y2": xyxy[3] / h,
                    })

            # Atomic replacement
            self.latest_detections = detections


#  Singleton 
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
