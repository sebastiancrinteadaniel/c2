import logging

from app.config.server import get_server_settings


_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure application logging once using server settings."""
    cfg = get_server_settings()
    level_name = cfg.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format=_LOG_FORMAT, force=True)