"""WebRTC camera track utilities for browser streaming."""

from __future__ import annotations

import logging
import queue
import threading
from collections import deque

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from app.services.yolo_processor import get_shared_yolo_processor


logger = logging.getLogger(__name__)


def _safe_put(q: queue.Queue, item) -> None:
    """Drop the oldest queue item when full to keep frames fresh."""
    if q.full():
        try:
            q.get_nowait()
        except queue.Empty:
            pass
    q.put_nowait(item)


class CvFpsCalc:
    """Compute FPS from OpenCV ticks with a rolling average."""

    def __init__(self, buffer_len: int = 10) -> None:
        self._start_tick = cv2.getTickCount()
        self._freq = 1000.0 / cv2.getTickFrequency()
        self._difftimes: deque[float] = deque(maxlen=buffer_len)

    def get(self) -> float:
        current_tick = cv2.getTickCount()
        different_time = (current_tick - self._start_tick) * self._freq
        self._start_tick = current_tick
        self._difftimes.append(different_time)

        if not self._difftimes:
            return 0.0

        fps = 1000.0 / (sum(self._difftimes) / len(self._difftimes))
        return round(fps, 2)


class CameraStreamTrack(VideoStreamTrack):
    """A simple webcam-backed WebRTC video track."""

    def __init__(self) -> None:
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self.yolo_processor = get_shared_yolo_processor()
        self.latest_detections = []
        self._stop_event = threading.Event()
        self._frame_queue: queue.Queue = queue.Queue(maxsize=1)
        self._result_queue: queue.Queue = queue.Queue(maxsize=1)

        self._last_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self._last_detections: list = []
        self._fps_counter = CvFpsCalc(buffer_len=10)
        self.current_fps = 0.0
        cv2.putText(
            self._last_frame,
            "WAITING FOR CAMERA",
            (420, 360),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        self._inference_thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._inference_thread.start()

    def _capture_loop(self) -> None:
        while not self._stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                continue
            _safe_put(self._frame_queue, frame)

    def _inference_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                frame = self._frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            annotated, detections = self.yolo_processor.process(frame)
            _safe_put(self._result_queue, (annotated, detections))

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        try:
            frame, detections = self._result_queue.get_nowait()
            self._last_frame = frame
            self._last_detections = detections
        except queue.Empty:
            frame = self._last_frame
            detections = self._last_detections

        self.latest_detections = detections
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.current_fps = self._fps_counter.get()
        video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def stop(self) -> None:
        self._stop_event.set()
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().stop()
