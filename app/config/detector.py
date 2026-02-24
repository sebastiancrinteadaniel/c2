from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectorSettings(BaseSettings):
    """
    YOLOv8 object detection configuration.

    Example .env:
        DETECTOR_ENABLED=true
        MODEL_PATH=yolov8n.pt
        CONFIDENCE=0.45
        IOU=0.45
        DEVICE=          # empty = auto (GPU if available, else CPU)
        INFER_SKIP_FRAMES=0   # 0 = every frame, 2 = every 3rd frame
        BOX_COLOR_B=0
        BOX_COLOR_G=212
        BOX_COLOR_R=255
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    detector_enabled:    bool  = True
    model_path:          str   = "models/yolov8n.pt"
    confidence:          float = 0.45
    iou:                 float = 0.45
    device:              str   = ""         # "" = ultralytics auto-select
    infer_skip_frames:   int   = 0          # run every N+1 frames

    # Bounding box overlay colour (BGR) — defaults to dashboard cyan
    box_color_b: int = 0
    box_color_g: int = 212
    box_color_r: int = 255


@lru_cache(maxsize=1)
def get_detector_settings() -> DetectorSettings:
    return DetectorSettings()
