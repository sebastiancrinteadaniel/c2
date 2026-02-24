from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """
    FastAPI / uvicorn server configuration.

    Example .env:
        HOST=0.0.0.0
        PORT=8000
        RELOAD=false
        LOG_LEVEL=info
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    host:      str  = "0.0.0.0"
    port:      int  = 8000
    reload:    bool = False
    log_level: str  = "info"


@lru_cache(maxsize=1)
def get_server_settings() -> ServerSettings:
    """Return the singleton ServerSettings instance (cached after first call)."""
    return ServerSettings()
