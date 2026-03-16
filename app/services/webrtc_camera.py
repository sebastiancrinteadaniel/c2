"""WebRTC camera track utilities for browser streaming."""

from __future__ import annotations

import asyncio
import time
import logging
from collections import deque

import cv2
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame


logger = logging.getLogger(__name__)


class RollingFpsCounter:
    """Compute FPS from recent frame timestamps."""

    def __init__(self, window_size: int = 30) -> None:
        self._timestamps: deque[float] = deque(maxlen=window_size)

    def tick(self) -> float:
        now = time.monotonic()
        self._timestamps.append(now)
        if len(self._timestamps) < 2:
            return 0.0

        elapsed = self._timestamps[-1] - self._timestamps[0]
        if elapsed <= 0:
            return 0.0

        return round((len(self._timestamps) - 1) / elapsed, 2)


class CameraStreamTrack(VideoStreamTrack):
    """A simple webcam-backed WebRTC video track."""

    def __init__(self) -> None:
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        self._last_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        self._fps_counter = RollingFpsCounter(window_size=30)
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

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()

        # Read frames off-thread to avoid blocking the event loop.
        ret, frame = await asyncio.to_thread(self.cap.read)
        if ret and frame is not None:
            self._last_frame = frame
        else:
            frame = self._last_frame

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.current_fps = self._fps_counter.tick()
        video_frame = VideoFrame.from_ndarray(rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

    def stop(self) -> None:
        if self.cap and self.cap.isOpened():
            self.cap.release()
        super().stop()
