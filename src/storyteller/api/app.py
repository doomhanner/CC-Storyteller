"""FastAPI application for CC-Storyteller web UI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from storyteller.api.routes import campaigns, codex, sessions, settings


def create_app(
    title: str = "CC-Storyteller API",
    debug: bool = False,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: API title
        debug: Enable debug mode
        cors_origins: List of allowed CORS origins

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title=title,
        description="LLM-powered narrative simulation engine API",
        version="0.1.0",
        debug=debug,
    )

    # Configure CORS
    if cors_origins is None:
        cors_origins = [
            "http://localhost:3000",  # Svelte dev server
            "http://localhost:5173",  # Vite dev server
            "http://localhost:8000",  # Same origin
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(settings.router, prefix="/api")
    app.include_router(campaigns.router, prefix="/api")
    app.include_router(codex.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "cc-storyteller"}

    # API info endpoint
    @app.get("/api")
    async def api_info():
        return {
            "name": "CC-Storyteller API",
            "version": "0.1.0",
            "endpoints": {
                "settings": "/api/settings",
                "campaigns": "/api/campaigns",
                "codex": "/api/codex/{campaign_id}",
                "sessions": "/api/sessions",
            },
        }

    return app


def create_app_with_static(
    static_dir: Path | str | None = None,
    **kwargs,
) -> FastAPI:
    """
    Create app with static file serving for production.

    Args:
        static_dir: Path to static files (built frontend)
        **kwargs: Additional arguments for create_app

    Returns:
        Configured FastAPI application with static files
    """
    app = create_app(**kwargs)

    if static_dir:
        static_path = Path(static_dir)
        if static_path.exists():
            # Serve static files
            app.mount("/", StaticFiles(directory=static_path, html=True), name="static")

    return app


# Default app instance for uvicorn
app = create_app()
