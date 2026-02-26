import uvicorn
from scalper_today.config import get_settings


def main() -> None:
    settings = get_settings()

    banner = f"""
+==============================================================+
|              ScalperToday API v{settings.app_version:<10}                    |
|              Clean Architecture Edition                      |
+==============================================================+
|  Environment: {settings.app_env:<20}                      |
|  AI Enabled:  {str(settings.is_ai_configured):<20}                      |
|  Server:      http://{settings.server_host}:{settings.server_port:<10}                  |
+==============================================================+
    """
    print(banner)

    uvicorn.run(
        "scalper_today.api.app:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
