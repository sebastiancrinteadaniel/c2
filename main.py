import uvicorn

from app.config.server import get_server_settings

if __name__ == "__main__":
    cfg = get_server_settings()
    uvicorn.run(
        "app.main:app",
        host=cfg.host,
        port=cfg.port,
        reload=cfg.reload,
        log_level=cfg.log_level,
    )

