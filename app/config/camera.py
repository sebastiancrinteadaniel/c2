from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CameraSettings(BaseSettings):
    """
    Camera resolution and capture configuration.

    Three independent resolution groups:

      capture  — physical resolution the camera grabs.
                 This is the quality ceiling; everything else is derived downward.

      infer    — resolution of the frame written to `latest_bgr_infer`.
                 Should always be ≤ capture. CV / object-detection reads here.

      display  — resolution encoded and sent over WebRTC to the browser.
                 Defaults to capture so there is zero resize and zero quality loss.

    All values can be overridden via environment variables or a .env file.

    Example .env:
        CAPTURE_WIDTH=1280
        CAPTURE_HEIGHT=720
        INFER_WIDTH=640
        INFER_HEIGHT=640
        DISPLAY_WIDTH=854
        DISPLAY_HEIGHT=480
        CAMERA_FPS=30
        CAMERA_INDEX=0
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Capture ───────────────────────────────────────────────────────────
    capture_width:  int = 1920
    capture_height: int = 1080

    # ── Inference ─────────────────────────────────────────────────────────
    infer_width:  int = 640
    infer_height: int = 640

    # ── Display (WebRTC stream) ───────────────────────────────────────────
    # -1 means "same as capture" — resolved in the validator below
    display_width:  int = -1
    display_height: int = -1

    # ── Misc ──────────────────────────────────────────────────────────────
    camera_fps:   int = 60
    camera_index: int = 0

    # ── WebRTC encoder bandwidth hint ─────────────────────────────────────
    webrtc_video_kbps: int = 4000

    @model_validator(mode="after")
    def _resolve_display_defaults(self) -> "CameraSettings":
        if self.display_width == -1:
            self.display_width = self.capture_width
        if self.display_height == -1:
            self.display_height = self.capture_height
        return self

    # ── Derived helpers ───────────────────────────────────────────────────
    @property
    def need_infer_resize(self) -> bool:
        return (self.infer_width != self.capture_width) or (
            self.infer_height != self.capture_height
        )

    @property
    def need_display_resize(self) -> bool:
        return (self.display_width != self.capture_width) or (
            self.display_height != self.capture_height
        )

    @property
    def display_upscales(self) -> bool:
        return (
            self.display_width > self.capture_width
            or self.display_height > self.capture_height
        )

    def summary(self) -> str:
        upscale_warn = "  ⚠ display > capture (upscale)" if self.display_upscales else ""
        return (
            f"device:{self.camera_index}  "
            f"capture:{self.capture_width}×{self.capture_height}  "
            f"infer:{self.infer_width}×{self.infer_height}  "
            f"display:{self.display_width}×{self.display_height}  "
            f"fps:{self.camera_fps}  "
            f"bitrate:{self.webrtc_video_kbps}kbps"
            f"{upscale_warn}"
        )


@lru_cache(maxsize=1)
def get_camera_settings() -> CameraSettings:
    """Return the singleton CameraSettings instance (cached after first call)."""
    return CameraSettings()
