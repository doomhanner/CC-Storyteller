"""FastAPI application for CC-Storyteller web UI."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from storyteller.api.routes import campaigns, codex, sessions, settings
from storyteller.api.routes.settings import setup_router


# Find the frontend dist directory
def _find_frontend_dist() -> Path | None:
    """Find the built frontend directory."""
    # Check relative to this file
    api_dir = Path(__file__).parent
    project_root = api_dir.parent.parent.parent

    dist_path = project_root / "frontend" / "dist"
    if dist_path.exists():
        return dist_path

    # Check relative to cwd
    cwd_dist = Path.cwd() / "frontend" / "dist"
    if cwd_dist.exists():
        return cwd_dist

    return None


def create_app(
    title: str = "CC-Storyteller API",
    debug: bool = False,
    cors_origins: list[str] | None = None,
    serve_frontend: bool = True,
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        title: API title
        debug: Enable debug mode
        cors_origins: List of allowed CORS origins
        serve_frontend: Whether to serve the built frontend

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
    app.include_router(setup_router, prefix="/api")
    app.include_router(campaigns.router, prefix="/api")
    app.include_router(codex.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "cc-storyteller"}

    # Setup status endpoint - check if first run
    @app.get("/api/setup/status")
    async def setup_status():
        """Check if initial setup has been completed."""
        from dotenv import dotenv_values

        env_path = Path.cwd() / ".env"
        is_configured = False
        has_env_file = env_path.exists()

        if has_env_file:
            env_values = dotenv_values(env_path)
            # Check if any API key is configured
            is_configured = bool(
                env_values.get("ANTHROPIC_API_KEY")
                or env_values.get("OPENAI_API_KEY")
                or env_values.get("GOOGLE_API_KEY")
            )

        return {
            "is_configured": is_configured,
            "has_env_file": has_env_file,
            "needs_setup": not is_configured,
        }

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
                "setup": "/api/setup/status",
            },
        }

    # Serve frontend if available
    frontend_dist = _find_frontend_dist()
    if serve_frontend and frontend_dist:
        # Mount static assets (js, css, etc.)
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        # Serve index.html for all non-API routes (SPA routing)
        @app.get("/{full_path:path}", response_class=HTMLResponse)
        async def serve_spa(request: Request, full_path: str):
            """Serve the SPA for all non-API routes."""
            # Don't serve SPA for API routes
            if full_path.startswith("api/"):
                return {"error": "Not found"}

            index_file = frontend_dist / "index.html"
            if index_file.exists():
                return FileResponse(index_file)

            return HTMLResponse(
                content="<h1>Frontend not built</h1><p>Run 'npm run build' in frontend/</p>",
                status_code=404,
            )

    return app


# Default app instance for uvicorn
# serve_frontend=True enables serving built frontend from frontend/dist/
app = create_app(serve_frontend=True)
