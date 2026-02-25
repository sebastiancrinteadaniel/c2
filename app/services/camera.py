from __future__ import annotations

import asyncio
import fractions
import threading
import time
from typing import Optional

import av
import cv2
from aiortc import MediaStreamTrack

from app.config.camera import CameraSettings, get_camera_settings
from app.config.detector import get_detector_settings


VIDEO_CLOCK_RATE = 90000
VIDEO_TIME_BASE  = fractions.Fraction(1, VIDEO_CLOCK_RATE)

#  Detection provider (set by detector service to avoid circular imports) 
_detection_provider = None


def set_detection_provider(fn) -> None:
    """Register a callable that returns the current list of Detection dicts."""
    global _detection_provider
    _detection_provider = fn


def _draw_detections(frame, detections: list, w: int, h: int) -> None:
    """Draw bounding boxes in-place on a BGR frame (display resolution)."""
    if not detections:
        return
    cfg = get_detector_settings()
    color = (cfg.box_color_b, cfg.box_color_g, cfg.box_color_r)
    for d in detections:
        x1 = int(d["x1"] * w)
        y1 = int(d["y1"] * h)
        x2 = int(d["x2"] * w)
        y2 = int(d["y2"] * h)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        label = f"{d['label']} {d['confidence']:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, cv2.FILLED)
        cv2.putText(
            frame, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA,
        )

class CameraStreamTrack(MediaStreamTrack):
    """
    VideoStreamTrack that reads from a local webcam in a background thread.

    Attributes
    ----------
    latest_bgr_infer : np.ndarray | None
        Most recent BGR frame at INFER resolution.
        CV inference reads this - copy it if you need to hold the array
        beyond a single frame interval.
    """

    kind = "video"

    def __init__(self) -> None:
        super().__init__()
        self._cap: Optional[cv2.VideoCapture] = None
        self._queue: asyncio.Queue[av.VideoFrame] = asyncio.Queue(maxsize=2)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._pts = 0
        self._cfg: Optional[CameraSettings] = None
        self.latest_bgr_infer: Optional[object] = None
        self.latest_bgr_display: Optional[object] = None
        self._infer_frame_id: int = 0

    @property
    def infer_frame_id(self) -> int:
        """Monotonically increasing counter, incremented for every new capture frame."""
        return self._infer_frame_id

    def start_capture(self) -> None:
        """Open the camera and start the background reader thread."""
        cfg = get_camera_settings()
        self._cfg = cfg

        self._cap = cv2.VideoCapture(cfg.camera_index)
        if not self._cap.isOpened():
            raise RuntimeError(f"Could not open camera at index {cfg.camera_index}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cfg.capture_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.capture_height)
        self._cap.set(cv2.CAP_PROP_FPS, cfg.camera_fps)

        self._running = True
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

        print(f"[camera] Started - {cfg.summary()}")

    def stop_capture(self) -> None:
        """Stop the background thread and release the camera."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()
        self.latest_bgr_infer = None
        self.latest_bgr_display = None
        print("[camera] Capture stopped")

    def _reader(self) -> None:
        cfg = self._cfg
        interval = 1.0 / cfg.camera_fps
        while self._running:
            t0 = time.monotonic()
            ret, bgr = self._cap.read()
            if not ret:
                time.sleep(interval)
                continue

            #  Inference copy (downscaled from capture) 
            self.latest_bgr_infer = (
                cv2.resize(
                    bgr,
                    (cfg.infer_width, cfg.infer_height),
                    interpolation=cv2.INTER_LINEAR,
                )
                if cfg.need_infer_resize else bgr
            )
            self._infer_frame_id += 1

            #  Display copy (resized from capture for WebRTC) 
            display_bgr = (
                cv2.resize(
                    bgr,
                    (cfg.display_width, cfg.display_height),
                    interpolation=cv2.INTER_LINEAR,
                )
                if cfg.need_display_resize else bgr
            )
            self.latest_bgr_display = display_bgr

            #  Draw detections (if detector is running) 
            if _detection_provider is not None:
                dets = _detection_provider()
                if dets:
                    dh, dw = display_bgr.shape[:2]
                    _draw_detections(display_bgr, dets, dw, dh)

            #  BGR -> RGB -> av.VideoFrame 
            rgb = cv2.cvtColor(display_bgr, cv2.COLOR_BGR2RGB)
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")

            self._pts += int(VIDEO_CLOCK_RATE / cfg.camera_fps)
            frame.pts = self._pts
            frame.time_base = VIDEO_TIME_BASE

            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._put_frame(frame), self._loop
                )

            elapsed = time.monotonic() - t0
            sleep_for = interval - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    async def _put_frame(self, frame: av.VideoFrame) -> None:
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        await self._queue.put(frame)

    async def recv(self) -> av.VideoFrame:
        """Called by aiortc to get the next frame for a peer connection."""
        return await self._queue.get()


#  Singleton 
_camera_track: Optional[CameraStreamTrack] = None


def get_camera_track() -> CameraStreamTrack:
    """Return the application-wide singleton camera track."""
    global _camera_track
    if _camera_track is None:
        _camera_track = CameraStreamTrack()
    return _camera_track


def start_camera() -> None:
    get_camera_track().start_capture()


def stop_camera() -> None:
    global _camera_track
    if _camera_track is not None:
        _camera_track.stop_capture()
        _camera_track = None
